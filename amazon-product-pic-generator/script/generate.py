#!/usr/bin/env python3
"""
og-image2 生图脚本（OpenAI 兼容接口）

用法:
  python generate.py --prompt "一只猫在草地上"
  python generate.py --prompt "电商主图，白底，高质感" --n 2 --output ./output/
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional


def _find_env_file() -> Optional[Path]:
    """从脚本目录向上逐级查找 .env 文件"""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        current = current.parent
    return None


def load_api_key(env_file: Optional[str] = None) -> str:
    """
    读取 OG_IMAGE2_API_KEY：
    1. 优先使用 --env-file 指定路径
    2. 其次自动查找向上的 .env
    3. 最后回退系统环境变量
    """
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

    api_key = os.getenv("OG_IMAGE2_API_KEY", "").strip()
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print(
            "[ERROR] 未找到 OG_IMAGE2_API_KEY（或 OPENAI_API_KEY），请在 .env 或环境变量中设置",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """同时支持默认值展示与原样保留换行。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="og-image2 生图工具（OpenAI 兼容）",
        formatter_class=HelpFormatter,
        epilog="""
示例:
  python generate.py --prompt "商品海报，极简风格"
  python generate.py --prompt "咖啡广告图" --model og-image2-low --size 1024x1024 --n 2
  python generate.py --prompt "鞋类电商主图" --output ./output/ --json
        """,
    )
    parser.add_argument("--prompt", "-p", required=True, help="生图提示词")
    parser.add_argument("--model", "-m", default=os.getenv("OG_IMAGE2_MODEL", "og-image2-low"), help="模型名称")
    parser.add_argument("--size", default="1024x1024", help="图片尺寸")
    parser.add_argument(
        "--response-format",
        default="url",
        choices=["url", "b64_json"],
        help="返回格式（URL 或 Base64）",
    )
    parser.add_argument("--n", type=int, default=1, help="生成数量")
    parser.add_argument("--output", "-o", default=None, metavar="DIR", help="下载目录（仅 response-format=url 时有效）")
    parser.add_argument("--prefix", default="og_img", help="保存文件名前缀")
    parser.add_argument(
        "--api-url",
        default=os.getenv("OG_IMAGE2_API_URL", "http://10.0.0.97:8081/v1"),
        help="OpenAI 兼容 API Base URL",
    )
    parser.add_argument("--env-file", default=None, metavar="PATH", help="指定 .env 文件路径（默认自动查找）")
    parser.add_argument("--timeout", type=int, default=180, help="HTTP 请求超时时间（秒）")
    parser.add_argument("--json", action="store_true", dest="json_output", help="输出完整 JSON 响应")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n 必须 >= 1")
    return args


def post_json(url: str, api_key: str, payload: dict, timeout: int) -> dict:
    try:
        import requests
    except ImportError:
        print("[ERROR] 缺少 requests，请先执行: python -m pip install requests", file=sys.stderr)
        sys.exit(1)

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError:
        print(f"[ERROR] 非 JSON 响应: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)

    if resp.status_code >= 400:
        print(f"[ERROR] HTTP {resp.status_code}", file=sys.stderr)
        print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    return data


def download_image(url: str, save_path: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(resp.read())
        return str(save_path)
    except Exception as e:
        print(f"[ERROR] 下载失败 {url}: {e}", file=sys.stderr)
        return ""


def main() -> None:
    args = parse_args()
    api_key = load_api_key(args.env_file)
    endpoint = args.api_url.rstrip("/") + "/images/generations"

    payload = {
        "prompt": args.prompt,
        "model": args.model,
        "size": args.size,
        "response_format": args.response_format,
        "n": args.n,
    }

    print(f"[INFO] 接口: {endpoint}", file=sys.stderr)
    print(f"[INFO] 模型: {args.model}", file=sys.stderr)
    print(f"[INFO] 尺寸: {args.size}", file=sys.stderr)
    print(f"[INFO] 数量: {args.n}", file=sys.stderr)
    print(f"[INFO] 返回格式: {args.response_format}", file=sys.stderr)
    print("[INFO] 正在请求生图...", file=sys.stderr)

    resp_dict = post_json(endpoint, api_key, payload, args.timeout)

    if args.json_output:
        print(json.dumps(resp_dict, ensure_ascii=False, indent=2))
        return

    data = resp_dict.get("data", []) if isinstance(resp_dict, dict) else []
    if not isinstance(data, list) or not data:
        print("[ERROR] 响应中未找到 data", file=sys.stderr)
        print(json.dumps(resp_dict, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    urls = [item.get("url", "") for item in data if isinstance(item, dict) and item.get("url")]

    if args.output and args.response_format == "url":
        out_dir = Path(args.output)
        saved_files = []
        for idx, url in enumerate(urls, 1):
            filename = f"{args.prefix}_{idx:02d}.png"
            file_path = download_image(url, out_dir / filename)
            if file_path:
                saved_files.append(file_path)
                print(f"[保存] {file_path}", file=sys.stderr)

        result = {
            "status": "success",
            "model": args.model,
            "prompt": args.prompt,
            "count": len(saved_files),
            "files": saved_files,
            "urls": urls,
            "raw_count": len(data),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 默认仅输出 URL，保持轻量
    if urls:
        for idx, url in enumerate(urls, 1):
            print(f"[图片{idx}] {url}")
    else:
        # 如果 response_format=b64_json，直接输出结构化摘要
        result = {
            "status": "success",
            "model": args.model,
            "prompt": args.prompt,
            "count": len(data),
            "data": data,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
