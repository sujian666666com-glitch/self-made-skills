#!/usr/bin/env python3
"""Batch-generate Amazon Basic / Premium A+ module images via Linkfox GPT_2_IMAGE.

Input:
  --input-dir   Product folder with input/ reference images and optional output/basic|premium plans.
  --output-dir  Run output root (creates basic/ and premium/ subtrees).
  --reference   Local reference image path (default: input/image.png under input-dir).
  --api-url / --api-key  Gateway credentials (or OPENAI_BASE_URL / OPENAI_API_KEY).

Output:
  run-summary.json, per-type manifest.json, raw/*.png, modules/*.png

Dependencies:
  Python 3.10+, Pillow, scripts/ai-media linkfox CLIs on PATH via subprocess.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] pip install pillow", file=sys.stderr)
    sys.exit(1)

AI_MEDIA = Path(__file__).resolve().parents[4] / "scripts" / "ai-media"
if not AI_MEDIA.exists():
    AI_MEDIA = Path(__file__).resolve().parents[3].parent / "scripts" / "ai-media"

MODULES = [
    ("basic", "01-hero", 970, 500, "1:1"),
    ("basic", "02-benefits", 970, 500, "16:9"),
    ("basic", "03-feature", 970, 500, "16:9"),
    ("premium", "01-hero", 1464, 840, "1:1"),
    ("premium", "02-benefits", 1464, 840, "16:9"),
    ("premium", "03-feature", 1464, 840, "16:9"),
    ("premium", "04-lifestyle", 1464, 840, "16:9"),
    ("premium", "05-specs-trust", 1464, 840, "16:9"),
]

TEXT_HEAVY = {"02-benefits", "03-feature", "05-specs-trust"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Linkfox GPT_2_IMAGE Amazon A+ module batch runner")
    p.add_argument("--input-dir", required=True, help="Product workspace, e.g. skirt folder")
    p.add_argument("--output-dir", default=None, help="Run output root; default input-dir/output/linkfox-<ts>")
    p.add_argument("--reference", default=None, help="Reference image; default <input-dir>/input/image.png")
    p.add_argument("--api-url", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--resolution", default="2K")
    p.add_argument("--quality", default="high")
    p.add_argument("--forward", action="store_true")
    p.add_argument("--poll-timeout", type=int, default=900)
    p.add_argument("--only", default=None, help="Comma list: basic:01-hero,premium:02-benefits")
    return p.parse_args()


def run_cli(script: str, argv: list[str], env: dict[str, str]) -> dict:
    cmd = [sys.executable, str(AI_MEDIA / script), *argv, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"CLI failed ({script}): {proc.stderr or proc.stdout}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {script}: {proc.stdout[:500]}") from exc


def extract_task_id(data: dict) -> str:
    for path in (
        ("data", "data", "data", "id"),
        ("data", "data", "id"),
        ("data", "id"),
        ("id",),
    ):
        cur: object = data
        for key in path:
            if not isinstance(cur, dict):
                break
            cur = cur.get(key)
        else:
            if cur:
                return str(cur)
    raise RuntimeError(f"task id not found: {json.dumps(data)[:400]}")


def extract_result_url(data: dict) -> tuple[str, int, int]:
    inner = data.get("data", {})
    if isinstance(inner, dict):
        d2 = inner.get("data", inner)
        if isinstance(d2, dict):
            d3 = d2.get("data", d2)
            if isinstance(d3, dict):
                items = d3.get("resultList") or []
                if items and isinstance(items[0], dict) and items[0].get("url"):
                    it = items[0]
                    return str(it["url"]), int(it.get("width") or 0), int(it.get("height") or 0)
    urls = []
    _walk_urls(data, urls)
    if urls:
        return urls[0], 0, 0
    raise RuntimeError(f"result url not found: {json.dumps(data)[:400]}")


def _walk_urls(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() == "url" and isinstance(v, str) and v.startswith("http"):
                out.append(v)
            else:
                _walk_urls(v, out)
    elif isinstance(node, list):
        for item in node:
            _walk_urls(item, out)


def resize_cover(src: Path, dst: Path, size: tuple[int, int]) -> None:
    with Image.open(src) as im:
        im = im.convert("RGB")
        tw, th = size
        w, h = im.size
        scale = max(tw / w, th / h)
        resized = im.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - tw) // 2
        top = (resized.height - th) // 2
        cropped = resized.crop((left, top, left + tw, top + th))
        dst.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(dst, format="PNG", optimize=True)


def prompt_path(run_dir: Path, a_type: str, module: str) -> Path:
    base = run_dir / a_type / "prompts"
    for name in (f"{module}.txt", f"{module}-rerun-16x9.txt"):
        p = base / name
        if p.exists():
            return p
    legacy = Path(args_input_dir) / "output" / a_type / "prompts" / f"{module}.txt"
    if legacy.exists():
        return legacy
    raise FileNotFoundError(f"prompt missing for {a_type}/{module}")


def shell_extra(prompt: str) -> str:
    escaped = prompt.replace("\\", "\\\\").replace('"', '\\"')
    return f'prompt="{escaped}"'


args_input_dir: Path


def main() -> None:
    global args_input_dir
    args = parse_args()
    args_input_dir = Path(args.input_dir).resolve()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.output_dir).resolve() if args.output_dir else args_input_dir / "output" / f"linkfox-gpt2image-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    ref = Path(args.reference) if args.reference else args_input_dir / "input" / "image.png"
    if not ref.exists():
        ref = args_input_dir / "image.png"
    if not ref.exists():
        raise SystemExit(f"[ERROR] reference image not found: {ref}")

    env = {**dict(__import__("os").environ)}
    if args.api_url:
        env["OPENAI_BASE_URL"] = args.api_url
    if args.api_key:
        env["OPENAI_API_KEY"] = args.api_key

    gateway = ["--api-url", args.api_url] if args.api_url else []
    if args.api_key:
        gateway += ["--api-key", args.api_key]
    if args.forward:
        gateway.append("--forward")

    upload = run_cli(
        "linkfox/image-upload-base64.py",
        ["--file", str(ref), *gateway],
        env,
    )
    image_url = None
    d = upload.get("data", {})
    if isinstance(d, dict):
        inner = d.get("data", d)
        if isinstance(inner, dict):
            deeper = inner.get("data", inner)
            if isinstance(deeper, dict) and deeper.get("viewUrl"):
                image_url = str(deeper["viewUrl"])
            elif inner.get("viewUrl"):
                image_url = str(inner["viewUrl"])
    if not image_url:
        raise RuntimeError(f"upload viewUrl missing: {json.dumps(upload)[:500]}")

    only = None
    if args.only:
        only = {x.strip() for x in args.only.split(",") if x.strip()}

    submitted: list[dict] = []
    completed: list[dict] = []

    for a_type, module, width, height, aspect in MODULES:
        key = f"{a_type}:{module}"
        if only and key not in only:
            continue

        prompts_src = args_input_dir / "output" / a_type / "prompts"
        prompts_dst = run_dir / a_type / "prompts"
        if prompts_src.exists() and not (prompts_dst / f"{module}.txt").exists():
            prompts_dst.mkdir(parents=True, exist_ok=True)
            for f in prompts_src.glob("*.txt"):
                if f.stem == module or f.stem.startswith(module):
                    (prompts_dst / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

        prompt_file = prompt_path(run_dir, a_type, module)
        prompt = prompt_file.read_text(encoding="utf-8").strip()
        if module in TEXT_HEAVY and "16:9" not in prompt_file.stem:
            rerun = prompts_dst / f"{module}-rerun-16x9.txt"
            if rerun.exists():
                prompt = rerun.read_text(encoding="utf-8").strip()

        submit_argv = [
            "--image",
            image_url,
            "--provider",
            "GPT_2_IMAGE",
            "--resolution",
            args.resolution,
            "--quality",
            args.quality,
            "--aspect-ratio",
            aspect,
            "--output-num",
            "1",
            "--extra",
            shell_extra(prompt),
            *gateway,
        ]
        submit_resp = run_cli("linkfox/multi-image-fusion-v2.py", submit_argv, env)
        task_id = extract_task_id(submit_resp)
        submitted.append({"a_plus_type": a_type, "module": module, "task_id": task_id, "aspect_ratio": aspect})

        query_argv = [
            task_id,
            "--wait",
            "--poll-timeout",
            str(args.poll_timeout),
            *gateway,
        ]
        query_resp = run_cli("linkfox/query.py", query_argv, env)
        url, sw, sh = extract_result_url(query_resp)

        raw_dir = run_dir / a_type / "raw"
        mod_dir = run_dir / a_type / "modules"
        raw_path = raw_dir / f"{module}.png"
        mod_path = mod_dir / f"{module}.png"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(resp.read())
        resize_cover(raw_path, mod_path, (width, height))
        completed.append(
            {
                "a_plus_type": a_type,
                "module": module,
                "task_id": task_id,
                "target_size": {"width": width, "height": height},
                "aspect_ratio": aspect,
                "raw_file": str(raw_path),
                "file": str(mod_path),
                "source_width": sw,
                "source_height": sh,
            }
        )
        print(f"[OK] {a_type}/{module} -> {mod_path}", flush=True)

    summary = {"status": "success", "run_dir": str(run_dir), "reference_url": image_url, "submitted_tasks": submitted, "completed_modules": completed}
    (run_dir / "run-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
