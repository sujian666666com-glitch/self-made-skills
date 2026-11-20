#!/usr/bin/env python3
"""
Qwen Image 2.0 / 2.0-Pro image generation helper.

Inputs:
  --prompt plus optional --images URL_OR_PATH values.

Outputs:
  JSON result when --output is provided or --json-result is used; otherwise
  prints generated image URLs in the legacy text format.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


SIZE_RE = re.compile(r"^[1-9][0-9]{1,4}x[1-9][0-9]{1,4}$")


def _find_env_file() -> Path | None:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        current = current.parent
    return None


def load_api_key(env_file: str | None = None) -> str:
    try:
        from dotenv import load_dotenv

        if env_file:
            load_dotenv(env_file, override=True)
        else:
            found = _find_env_file()
            if found:
                load_dotenv(found, override=True)
    except ImportError:
        target = Path(env_file) if env_file else _find_env_file()
        if target and target.exists():
            with open(target, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未找到 DASHSCOPE_API_KEY，请在 .env 文件或环境变量中设置")
    return api_key


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Show defaults while preserving examples."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qwen Image 2.0 / 2.0-Pro 生图工具",
        formatter_class=HelpFormatter,
        epilog="""
Examples:
  python generate.py --prompt "一只猫在草地上"
  python generate.py --model qwen-image-2.0-pro \
      --images ./product.png \
      --prompt "Create a clean product image" \
      --size 750x600 \
      --output ./output \
      --json-result
        """,
    )
    parser.add_argument(
        "--model",
        "-m",
        default="qwen-image-2.0",
        choices=["qwen-image-2.0", "qwen-image-2.0-pro"],
        help="使用的模型",
    )
    parser.add_argument(
        "--images",
        "-i",
        nargs="*",
        default=[],
        metavar="URL_OR_PATH",
        help="参考图列表，支持 URL 或本地路径",
    )
    parser.add_argument("--prompt", "-p", required=True, help="生图文字提示词")
    parser.add_argument(
        "--negative-prompt",
        "--neg",
        default="",
        dest="negative_prompt",
        help="负向提示词",
    )
    parser.add_argument("--n", type=int, default=1, metavar="N", help="生成数量，1-4")
    parser.add_argument(
        "--watermark",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="水印开关",
    )
    parser.add_argument("--seed", type=int, default=None, metavar="INT", help="随机种子")
    parser.add_argument(
        "--size",
        default=None,
        metavar="WIDTHxHEIGHT",
        help="期望输出尺寸，例如 750x600；若上游模型支持则传递给 API，同时写入结果元数据",
    )
    parser.add_argument("--output", "-o", default=None, metavar="DIR", help="输出目录")
    parser.add_argument("--prefix", default="qwen_img", help="保存文件名前缀")
    parser.add_argument("--json", action="store_true", dest="json_output", help="打印完整 API 响应")
    parser.add_argument(
        "--json-result",
        action="store_true",
        help="只打印精简结构化结果，供上层脚本解析",
    )
    parser.add_argument(
        "--api-url",
        default="https://dashscope.aliyuncs.com/api/v1",
        metavar="URL",
        help="DashScope API 地址",
    )
    parser.add_argument("--env-file", default=None, metavar="PATH", help="指定 .env 文件路径")

    args = parser.parse_args()
    if not 1 <= args.n <= 4:
        parser.error("--n 必须在 1-4 之间")
    if args.size and not SIZE_RE.match(args.size):
        parser.error("--size 必须使用 WIDTHxHEIGHT 格式，例如 750x600")
    return args


def emit_error(code: str, message: str, *, status_code: int = 1, detail: object | None = None) -> int:
    payload = {"status": "error", "code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[ERROR] {message}", file=sys.stderr)
    return status_code


def _image_to_content(path_or_url: str) -> dict:
    if path_or_url.startswith(("http://", "https://")):
        return {"image": path_or_url}

    local = Path(path_or_url)
    if not local.exists():
        print(f"[WARN] 图片文件不存在，跳过: {path_or_url}", file=sys.stderr)
        return {}

    suffix = local.suffix.lstrip(".").lower() or "png"
    with open(local, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return {"image": f"data:image/{suffix};base64,{encoded}"}


def build_messages(images: list[str], prompt: str) -> list[dict]:
    content = []
    for image in images:
        item = _image_to_content(image)
        if item:
            content.append(item)
    content.append({"text": prompt})
    return [{"role": "user", "content": content}]


def response_to_dict(response) -> dict:
    if isinstance(response, dict):
        return response
    try:
        return {
            "status_code": getattr(response, "status_code", None),
            "request_id": getattr(response, "request_id", None),
            "code": getattr(response, "code", None),
            "message": getattr(response, "message", None),
            "output": dict(response.output) if hasattr(response, "output") else {},
            "usage": dict(response.usage) if hasattr(response, "usage") else {},
        }
    except Exception:
        return {}


def extract_image_urls(resp_dict: dict) -> list[str]:
    urls: list[str] = []
    choices = resp_dict.get("output", {}).get("choices", []) or []
    for choice in choices:
        content_list = choice.get("message", {}).get("content", []) or []
        for item in content_list:
            if not isinstance(item, dict):
                continue
            if "image" in item:
                urls.append(item["image"])
            elif item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if url:
                    urls.append(url)
    return urls


def download_image(url: str, save_path: Path) -> str:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            save_path.write_bytes(response.read())
        return str(save_path)
    except Exception as exc:
        print(f"[ERROR] 下载图片失败 {url}: {exc}", file=sys.stderr)
        return ""


def build_result(args: argparse.Namespace, files: list[str], urls: list[str], usage: dict) -> dict:
    return {
        "status": "success",
        "model": args.model,
        "prompt": args.prompt,
        "requested_size": args.size,
        "count": len(files) if files else len(urls),
        "files": files,
        "urls": urls,
        "usage": usage,
    }


def main() -> int:
    args = parse_args()

    try:
        api_key = load_api_key(args.env_file)

        import dashscope
        from dashscope import MultiModalConversation

        dashscope.base_http_api_url = args.api_url
        messages = build_messages(args.images, args.prompt)

        print(f"[INFO] 模型: {args.model}", file=sys.stderr)
        print(f"[INFO] 参考图片数: {len(args.images)}", file=sys.stderr)
        print(f"[INFO] 生成数量: {args.n}", file=sys.stderr)
        if args.size:
            print(f"[INFO] 期望尺寸: {args.size}", file=sys.stderr)

        call_kwargs = {
            "api_key": api_key,
            "model": args.model,
            "messages": messages,
            "result_format": "message",
            "stream": False,
            "n": args.n,
            "watermark": args.watermark,
            "negative_prompt": args.negative_prompt,
        }
        if args.seed is not None:
            call_kwargs["seed"] = args.seed
        if args.size:
            call_kwargs["size"] = args.size.replace("x", "*")

        print("[INFO] 正在调用 API，请稍候...", file=sys.stderr)
        response = MultiModalConversation.call(**call_kwargs)
        resp_dict = response_to_dict(response)

        if args.json_output:
            print(json.dumps(resp_dict, ensure_ascii=False, indent=2))
            return 0

        status_code = resp_dict.get("status_code")
        if status_code != 200:
            return emit_error(
                "api_error",
                f"API 返回错误 (status={status_code}): {resp_dict.get('message', '')}",
                detail=resp_dict,
            )

        image_urls = extract_image_urls(resp_dict)
        if not image_urls:
            return emit_error("no_image_urls", "响应中未找到生成的图片", detail=resp_dict)

        saved: list[str] = []
        if args.output:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            for idx, url in enumerate(image_urls, 1):
                path = out_dir / f"{args.prefix}_{idx:02d}.png"
                result_path = download_image(url, path)
                if result_path:
                    saved.append(result_path)
                    print(f"[保存] {result_path}", file=sys.stderr)

        result = build_result(args, saved, image_urls, resp_dict.get("usage", {}))
        if args.output or args.json_result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for idx, url in enumerate(image_urls, 1):
                print(f"[图片{idx}] {url}")
        return 0
    except Exception as exc:
        return emit_error(type(exc).__name__, str(exc))


if __name__ == "__main__":
    sys.exit(main())
