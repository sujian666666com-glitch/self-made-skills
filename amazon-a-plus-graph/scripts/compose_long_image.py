#!/usr/bin/env python3
"""Compose ecommerce long-detail step images into one checked long image."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] Missing dependency: Pillow. Install with: pip install pillow", file=sys.stderr)
    sys.exit(1)


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
STEP_IMAGE_RE = re.compile(r"^step-\d{2}-[a-z0-9-]+$")
RAW_STEP_IMAGE_RE = re.compile(r"^step-\d{2}-[a-z0-9-]+_\d{2}(?:_\d{2})?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose long-detail ecommerce section images into one final PNG."
    )
    parser.add_argument("--input", "-i", required=True, help="Input step image file or directory.")
    parser.add_argument("--output", "-o", required=True, help="Final long image path.")
    parser.add_argument("--width", type=int, default=750, help="Final image width.")
    parser.add_argument(
        "--source",
        choices=["normalized", "raw"],
        default="normalized",
        help="Use normalized step images or provider raw step images. Raw falls back to normalized when absent.",
    )
    parser.add_argument(
        "--compose-mode",
        choices=["stack", "blend"],
        default="stack",
        help="Stack sections directly or alpha blend adjacent sections.",
    )
    parser.add_argument("--overlap", type=int, default=40, help="Alpha blend overlap in pixels.")
    parser.add_argument(
        "--blend-mode",
        choices=["linear", "gaussian"],
        default="linear",
        help="Blend curve for adjacent sections.",
    )
    parser.add_argument("--max-mb", type=float, default=10.0, help="Warn when output exceeds this size.")
    parser.add_argument("--delta-e-threshold", type=float, default=15.0, help="Color jump warning threshold.")
    parser.add_argument("--manifest", default=None, help="Manifest output path; defaults near final image.")
    parser.add_argument("--review-file", default=None, help="Optional JSON file with review_required items.")
    return parser.parse_args()


def collect_images(path: Path, source: str) -> tuple[list[Path], str]:
    if path.is_file():
        return [path], "file"
    if path.is_dir():
        if source == "raw":
            raw_images = sorted(
                p
                for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and RAW_STEP_IMAGE_RE.match(p.stem)
            )
            if raw_images:
                return raw_images, "raw"
            normalized_images = sorted(
                p
                for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and STEP_IMAGE_RE.match(p.stem)
            )
            return normalized_images, "normalized-fallback"
        return sorted(
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and STEP_IMAGE_RE.match(p.stem)
        ), "normalized"
    raise FileNotFoundError(f"Input path not found: {path}")


def resize_to_width(path: Path, width: int) -> Image.Image:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if image.width == width:
            return image.copy()
        scale = width / image.width
        height = max(1, round(image.height * scale))
        return image.resize((width, height), Image.Resampling.LANCZOS)


def blend_weight(index: int, overlap: int, mode: str) -> float:
    t = (index + 1) / overlap
    if mode == "gaussian":
        return 0.5 - 0.5 * math.cos(math.pi * t)
    return t


def srgb_to_linear(channel: float) -> float:
    channel = channel / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (srgb_to_linear(c) for c in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883

    def f(value: float) -> float:
        if value > 0.008856:
            return value ** (1 / 3)
        return 7.787 * value + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def average_rgb(image: Image.Image) -> tuple[float, float, float]:
    pixel = image.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return tuple(float(v) for v in pixel)


def delta_e(a: Image.Image, b: Image.Image) -> float:
    lab_a = rgb_to_lab(average_rgb(a))
    lab_b = rgb_to_lab(average_rgb(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(lab_a, lab_b)))


def compose(images: list[Image.Image], overlap: int, mode: str) -> Image.Image:
    if not images:
        raise ValueError("No images to compose")
    if len(images) == 1 or overlap <= 0:
        height = sum(image.height for image in images)
        canvas = Image.new("RGB", (images[0].width, height), "white")
        y = 0
        for image in images:
            canvas.paste(image, (0, y))
            y += image.height
        return canvas

    safe_overlap = min(overlap, *(image.height // 3 for image in images))
    height = images[0].height + sum(image.height - safe_overlap for image in images[1:])
    canvas = Image.new("RGB", (images[0].width, height), "white")
    y = 0
    canvas.paste(images[0], (0, y))
    y += images[0].height

    for image in images[1:]:
        blend_y = y - safe_overlap
        previous_strip = canvas.crop((0, blend_y, canvas.width, y))
        current_strip = image.crop((0, 0, image.width, safe_overlap))
        blended = Image.new("RGB", (canvas.width, safe_overlap), "white")
        for row in range(safe_overlap):
            weight = blend_weight(row, safe_overlap, mode)
            previous_row = previous_strip.crop((0, row, canvas.width, row + 1))
            current_row = current_strip.crop((0, row, canvas.width, row + 1))
            blended_row = Image.blend(previous_row, current_row, weight)
            blended.paste(blended_row, (0, row))
        canvas.paste(blended, (0, blend_y))
        canvas.paste(image.crop((0, safe_overlap, image.width, image.height)), (0, y))
        y += image.height - safe_overlap

    return canvas


def load_review_required(path: str | None) -> list[str]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        value = data.get("review_required") or data.get("risk_notes") or []
        return [str(item) for item in value]
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def main() -> None:
    args = parse_args()
    input_paths, resolved_source = collect_images(Path(args.input), args.source)
    if not input_paths:
        print("[ERROR] No input images found.", file=sys.stderr)
        sys.exit(1)

    images = [resize_to_width(path, args.width) for path in input_paths]
    warnings = []
    compose_overlap = 0 if args.compose_mode == "stack" else args.overlap
    safe_overlap = max(0, min(compose_overlap, *(image.height // 3 for image in images)))
    seam_check_px = safe_overlap or max(1, min(40, *(image.height // 3 for image in images)))
    for idx in range(len(images) - 1):
        if seam_check_px <= 0:
            continue
        bottom = images[idx].crop((0, images[idx].height - seam_check_px, args.width, images[idx].height))
        top = images[idx + 1].crop((0, 0, args.width, seam_check_px))
        value = delta_e(bottom, top)
        if value > args.delta_e_threshold:
            warnings.append(
                {
                    "type": "color_jump",
                    "between": [str(input_paths[idx]), str(input_paths[idx + 1])],
                    "delta_e": round(value, 2),
                    "threshold": args.delta_e_threshold,
                }
            )

    final = compose(images, compose_overlap, args.blend_mode)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output_format = "PNG"
    save_kwargs = {"optimize": True}
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        output_format = "JPEG"
        save_kwargs = {"quality": 95, "optimize": True}
    final.save(output, format=output_format, **save_kwargs)
    size_mb = output.stat().st_size / (1024 * 1024)
    if size_mb > args.max_mb:
        warnings.append(
            {
                "type": "file_size",
                "size_mb": round(size_mb, 3),
                "max_mb": args.max_mb,
            }
        )

    manifest_path = Path(args.manifest) if args.manifest else output.parent / "manifest.json"
    manifest = {
        "status": "success",
        "final_file": str(output),
        "width": final.width,
        "height": final.height,
        "source": args.source,
        "resolved_source": resolved_source,
        "compose_mode": args.compose_mode,
        "overlap": compose_overlap,
        "seam_check_px": seam_check_px,
        "blend_mode": args.blend_mode,
        "output_format": output_format,
        "size_mb": round(size_mb, 3),
        "steps": [
            {
                "section": path.stem,
                "file": str(path),
                "width": image.width,
                "height": image.height,
            }
            for path, image in zip(input_paths, images)
        ],
        "warnings": warnings,
        "review_required": load_review_required(args.review_file),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
