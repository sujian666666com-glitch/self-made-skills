#!/usr/bin/env python3
"""
Amazon Listing 图片批量生成工具
支持异步轮询模式 + 自动重试 + 串行/并发

API 特性:
- 生图接口 /images/generations 是异步的
- 成功时返回 {"created": ..., "data": [{"url": "..."}]}
- 队列满时返回 502 + task_id (RequestLimitExceeded)
- 超时也返回 task_id
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent


def _find_env_file() -> Optional[Path]:
    current = SCRIPT_DIR
    for _ in range(5):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        current = current.parent
    return None


def load_api_key(env_file: Optional[str] = None) -> str:
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
        print("[ERROR] 未找到 OG_IMAGE2_API_KEY", file=sys.stderr)
        sys.exit(1)
    return api_key


def submit_generation(api_url: str, api_key: str, payload: dict, timeout: int = 600) -> dict:
    """提交生图请求，返回完整响应"""
    try:
        import requests
    except ImportError:
        print("[ERROR] pip install requests", file=sys.stderr)
        sys.exit(1)

    resp = requests.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    return resp


def poll_task(task_url: str, api_key: str, interval: int = 15, max_wait: int = 600) -> Optional[dict]:
    """轮询任务直到完成，返回 data 数组"""
    import requests

    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            r = requests.get(task_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
            data = r.json()
        except Exception as e:
            time.sleep(interval)
            continue

        # 成功
        if r.status_code == 200 and "data" in data:
            return data.get("data", [])

        # 完成
        status = data.get("status", "")
        if status == "succeeded":
            result = data.get("result", {})
            image_url = result.get("image_url") or result.get("output_url") or result.get("url", "")
            if image_url:
                return [{"url": image_url}]

        if status == "failed":
            print(f"[POLL] Task failed: {json.dumps(data, ensure_ascii=False)[:200]}", file=sys.stderr)
            return None

        # 还在进行中
        time.sleep(interval)

    print(f"[POLL] Timeout after {max_wait}s", file=sys.stderr)
    return None


def extract_image_urls(resp_data: dict, base_url: str, api_key: str) -> Optional[list]:
    """从响应中提取图片 URL 列表"""
    # 直接返回 data
    data = resp_data.get("data", [])
    if isinstance(data, list) and data:
        urls = [item.get("url", "") for item in data if isinstance(item, dict) and item.get("url")]
        if urls:
            return urls

    # 返回 task_id 需要轮询
    task_id = resp_data.get("task_id", "")
    if not task_id:
        # 可能嵌套在 error 里
        err = resp_data.get("error", {})
        if isinstance(err, dict):
            task_id = err.get("task_id", "")

    if task_id:
        # 尝试多个 poll 路径
        poll_paths = [
            f"{base_url}/tencent/vod/tasks/{task_id}",
            f"{base_url}/tasks/{task_id}",
        ]
        for poll_url in poll_paths:
            urls = poll_task(poll_url, api_key)
            if urls:
                return urls

    return None


def download_image(url: str, save_path: Path, timeout: int = 120) -> str:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(resp.read())
    return str(save_path)


def generate_one_image(
    prompt: str,
    prefix: str,
    task_type: str,
    api_url: str,
    api_key: str,
    output_dir: Path,
    model: str,
    size: str,
    max_retries: int = 3,
    retry_delay: int = 30,
) -> dict:
    """生成单张图片（含自动重试 + 异步轮询）"""
    if not prompt:
        return {"type": task_type, "status": "skipped", "reason": "empty prompt", "prefix": prefix}

    payload = {
        "prompt": prompt,
        "model": model,
        "size": size,
        "response_format": "url",
        "n": 1,
    }

    print(f"[{task_type}] 提交请求... prompt={prompt[:60]}...", file=sys.stderr)
    t0 = time.time()

    for attempt in range(1, max_retries + 1):
        try:
            resp = submit_generation(api_url, api_key, payload, timeout=600)
            resp_data = resp.json()
            st = resp.status_code

            if st == 200:
                urls = extract_image_urls(resp_data, api_url, api_key)
                if urls and urls[0]:
                    # 下载
                    filename = f"{prefix}.png"
                    file_path = output_dir / filename
                    try:
                        saved = download_image(urls[0], file_path)
                        elapsed = round(time.time() - t0, 1)
                        print(f"[{task_type}] ✅ 成功! {saved} ({elapsed}s)", file=sys.stderr)
                        return {
                            "type": task_type,
                            "status": "success",
                            "prefix": prefix,
                            "prompt": prompt,
                            "files": [saved],
                            "urls": urls,
                            "elapsed": elapsed,
                        }
                    except Exception as e:
                        print(f"[{task_type}] 下载失败: {e}", file=sys.stderr)
                        return {"type": task_type, "status": "error", "reason": f"download failed: {e}", "prefix": prefix, "elapsed": round(time.time() - t0, 1)}

            # 502 限流
            if st == 502:
                wait = retry_delay * attempt
                task_id = resp_data.get("task_id", "") or (resp_data.get("error", {}).get("task_id", "") if isinstance(resp_data, dict) else "")
                reason = resp_data.get("error", {}).get("message", "502")[:80] if isinstance(resp_data, dict) else "502"
                print(f"[{task_type}] 限流(502)，{wait}s 后重试... ({reason})", file=sys.stderr)
                time.sleep(wait)
                continue

            # 其他错误
            err_msg = json.dumps(resp_data, ensure_ascii=False)[:150]
            elapsed = round(time.time() - t0, 1)
            return {"type": task_type, "status": "error", "reason": f"HTTP {st}: {err_msg}", "prefix": prefix, "elapsed": elapsed}

        except Exception as e:
            if attempt < max_retries:
                wait = retry_delay * attempt
                print(f"[{task_type}] 异常: {e}, {wait}s 后重试...", file=sys.stderr)
                time.sleep(wait)
            else:
                return {"type": task_type, "status": "error", "reason": str(e), "prefix": prefix, "elapsed": round(time.time() - t0, 1)}

    elapsed = round(time.time() - t0, 1)
    return {"type": task_type, "status": "error", "reason": "max retries exceeded", "prefix": prefix, "elapsed": elapsed}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon Listing 图片批量生成",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tasks", "-t", required=True, help="JSON 任务文件")
    parser.add_argument("--output", "-o", required=True, help="输出目录")
    parser.add_argument("--model", "-m", default=os.getenv("OG_IMAGE2_MODEL", "og-image2-low"))
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--timeout", type=int, default=600, help="单任务超时(秒)")
    parser.add_argument("--retry-delay", type=int, default=30, help="重试间隔(秒)")
    parser.add_argument("--sequential", action="store_true", help="串行执行（默认）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tasks_path = Path(args.tasks)
    if not tasks_path.exists():
        print(f"[ERROR] 不存在: {tasks_path}", file=sys.stderr)
        sys.exit(1)

    with open(tasks_path, encoding="utf-8") as f:
        tasks_data = json.load(f)

    if isinstance(tasks_data, list):
        tasks = tasks_data
        product_name = ""
    else:
        tasks = tasks_data.get("tasks", [])
        product_name = tasks_data.get("product_name", "")

    if not tasks:
        print("[ERROR] 任务为空", file=sys.stderr)
        sys.exit(1)

    if product_name:
        print(f"[INFO] 产品: {product_name}", file=sys.stderr)
    print(f"[INFO] 共 {len(tasks)} 个任务, 串行模式, 尺寸 {args.size}", file=sys.stderr)

    api_key = load_api_key(args.env_file)
    api_url = os.getenv("OG_IMAGE2_API_URL", "http://10.0.0.97:8081/v1").rstrip("/") + "/images/generations"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for task in tasks:
        r = generate_one_image(
            prompt=task.get("prompt", ""),
            prefix=task.get("prefix", task.get("type", "img")),
            task_type=task.get("type", "unknown"),
            api_url=api_url,
            api_key=api_key,
            output_dir=output_dir,
            model=args.model,
            size=args.size,
            retry_delay=args.retry_delay,
        )
        results.append(r)

    # 汇总
    print("\n===== 生成汇总 =====", file=sys.stderr)
    success = errors = total_files = 0
    for r in results:
        icon = "✅" if r.get("status") == "success" else "❌"
        files = r.get("files", [])
        total_files += len(files)
        if r.get("status") == "success":
            success += 1
        else:
            errors += 1
        elapsed = r.get("elapsed", "?")
        reason = f" ({r.get('reason', '')})" if r.get("status") != "success" else ""
        print(f"  {icon} {r['type']}: {r['status']}{reason} ({len(files)}张, {elapsed}s)", file=sys.stderr)

    print(f"\n  总计: {success} 成功, {errors} 失败, {total_files} 张图片", file=sys.stderr)
    print(f"  输出: {output_dir}", file=sys.stderr)

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "product": product_name,
            "model": args.model,
            "size": args.size,
            "total_tasks": len(tasks),
            "success": success,
            "errors": errors,
            "total_files": total_files,
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"  元数据: {meta_path}", file=sys.stderr)
    print("\n===== 完成 =====", file=sys.stderr)


if __name__ == "__main__":
    main()
