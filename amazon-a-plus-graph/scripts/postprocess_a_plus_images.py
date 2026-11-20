#!/usr/bin/env python3
"""Resize, crop, rename, and check Amazon A+ image assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] Missing dependency: Pillow. Install with: pip install pillow", file=sys.stderr)
    sys.exit(1)


PROFILES = {
    "basic": {
        "size": (970, 300),
        "names": [
            "01-white-product.png",
            "02-origin-scene.png",
            "03-portable-benefit.png",
            "04-core-benefits.png",
            "05-specs-usage.png",
        ],
    },
    "premium": {
        "size": (1464, 600),
        "names": [
            "01-hero.png",
            "02-benefits.png",
            "03-scenario.png",
            "04-hotspot.png",
            "05-specs.png",
            "06-comparison.png",
            "07-faq.png",
        ],
    },
    "brand-story": {
        "size": (1500, 500),
        "names": [
            "01-brand.png",
            "02-origin.png",
            "03-mission.png",
            "04-product-line.png",
            "05-trust.png",
            "06-store.png",
        ],
    },
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post-process Amazon A+ images to exact output dimensions."
    )
    parser.add_argument("--input", "-i", required=True, help="Input image file or directory.")
    parser.add_argument("--output", "-o", required=True, help="Output directory.")
    parser.add_argument(
        "--profile",
        "-p",
        default="basic",
        choices=sorted(PROFILES),
        help="A+ output profile.",
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=2.0,
        help="Warn when an output image exceeds this size in MB.",
    )
    parser.add_argument(
        "--fit",
        choices=["cover", "contain"],
        default="contain",
        help="contain preserves the full composition with padding; cover crops to fill the target.",
    )
    return parser.parse_args()


def collect_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file())
    raise FileNotFoundError(f"Input path not found: {path}")


def resize_cover(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    width, height = image.size
    target_w, target_h = target
    scale = max(target_w / width, target_h / height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def resize_contain(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    width, height = image.size
    target_w, target_h = target
    scale = min(target_w / width, target_h / height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", target, "white")
    left = (target_w - resized.width) // 2
    top = (target_h - resized.height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def normalize_image(path: Path, target: tuple[int, int], fit: str) -> Image.Image:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if fit == "contain":
            return resize_contain(image, target)
        return resize_cover(image, target)


def output_name(index: int, profile: str, original: Path) -> str:
    if original.stem.startswith("00-white-background"):
        return "00-white-background.png"

    names = PROFILES[profile]["names"]
    if index < len(names):
        return names[index]
    return f"{index + 1:02d}-{original.stem}.png"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = collect_inputs(input_path)
    if not inputs:
        print("[ERROR] No input images found.", file=sys.stderr)
        sys.exit(1)

    profile = PROFILES[args.profile]
    target = profile["size"]
    results = []

    module_index = 0
    for src in inputs:
        is_white_master = src.stem.startswith("00-white-background")
        name = output_name(module_index, args.profile, src)
        if not is_white_master:
            module_index += 1
        dst = output_dir / name
        normalized = normalize_image(src, target, args.fit)
        normalized.save(dst, format="PNG", optimize=True)
        size_mb = dst.stat().st_size / (1024 * 1024)
        results.append(
            {
                "source": str(src),
                "file": str(dst),
                "width": target[0],
                "height": target[1],
                "size_mb": round(size_mb, 3),
                "over_limit": size_mb > args.max_mb,
            }
        )

    print(
        json.dumps(
            {
                "status": "success",
                "profile": args.profile,
                "fit": args.fit,
                "target_size": {"width": target[0], "height": target[1]},
                "count": len(results),
                "files": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
