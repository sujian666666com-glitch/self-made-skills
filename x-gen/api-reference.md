# X-GEN API Reference

Complete parameter reference for all XXZ API endpoints.

## Endpoints Summary

| Model | Endpoint | Method | Flow |
|-------|----------|--------|------|
| nano-banana-2 | `/v1/images/generations` | POST | Sync |
| nano-banana-pro | `/v1/images/generations` | POST | Sync |
| nano-banana-official | `/api/generate/nano-banana-official` | POST | Sync (Base64) |
| nano-banana-2-w | `/v1/images/generations/async` | POST | Async |
| nano-banana-2-w (poll) | `/v1/images/tasks/{task_id}` | GET | Poll |
| gpt-image-2 | `/v1/images/generations/async` | POST | Async (recommended) |
| gpt-image-2 (poll) | `/v1/images/tasks/{task_id}` | GET | Poll |
| gpt-image-2 (sync) | `/v1/images/generations` | POST | Sync (300s timeout limit) |
| grok-video-3 | `/api/generate/video-async` | POST | Async |
| grok-video-3-max | `/api/generate/video-async` | POST | Async |
| video poll | `/api/generate/video-async/poll/{id}` | GET | Poll |

## Image Parameters by Model

### nano-banana-2 & nano-banana-pro (Sync)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | `nano-banana-2` or `nano-banana-pro` |
| prompt | string | Yes | Image description |
| aspectRatio | string | No | See ratio table. `auto` (pro only) preserves source ratio |
| imageSize | string | No | `1K`, `2K`, `4K`. Default `1K` |
| n | integer | No | Number of images, default 1 |
| images | string[] | No | Reference image URLs for image-to-image |

### nano-banana-official (Sync, Base64 response)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | Image description |
| aspectRatio | string | No | Default `1:1`. Supports `9:16`, `16:9` |
| imageSize | string | No | `1K`, `2K`, `4K`. Default `1K` |
| n | integer | No | 1-4, default 1 |
| referenceImages | string[] | No | Base64-encoded image data |
| referenceMimeTypes | string[] | No | MIME types matching referenceImages |

### nano-banana-2-w (Async)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | `nano-banana-2-w` |
| prompt | string | Yes | Image description |
| size | string | No | `1K`, `2K`, `4K`. Default `1K` |
| aspectRatio | string | No | Default `auto` |
| urls | string[] | No | Reference image URLs for image-to-image |

### gpt-image-2 (Async recommended, pixel-based sizes)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | `gpt-image-2` |
| prompt | string | Yes | Image description |
| size | string | No | Pixel dimensions, default `1024x1024`. See size table below. Supports custom WxH (max 3840px, multiples of 16) |
| n | integer | No | Number of images, 1-10, default 1 |
| quality | string | No | `low`, `medium`, `high`, `auto` (default) |
| images | string[] | No | Reference images for image-to-image. Supports URL or base64 |
| mask | file | No | PNG mask for inpainting. Transparent area (alpha=0) = edit region. Must match image size, <4MB. Only applies to first reference image, only for 2K/4K/custom sizes |
| response_format | string | No | Fixed to `url` |

## Video Parameters

### grok-video-3 & grok-video-3-max

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | `grok-video-3` or `grok-video-3-max` |
| prompt | string | Yes | Video description |
| duration | integer | No | Seconds. See pricing table below |
| aspectRatio | string | No | grok-video-3: all ratios. grok-video-3-max: `9:16`, `16:9` only |
| image_urls | string[] | Conditional | Required for grok-video-3-max. Public URLs |

## Pricing Tables

### Image Models

| Model | 1K | 2K | 4K |
|-------|----|----|-----|
| nano-banana-2 | 10 cr | 10 cr | 15 cr |
| nano-banana-pro | 20 cr | 20 cr | 30 cr |
| nano-banana-official | 10 cr | 10 cr | 15 cr |
| nano-banana-2-w | 15 cr | 15 cr | 15 cr |

### gpt-image-2

| Size | Ratio | Credits/Image |
|------|-------|---------------|
| 1024x1024 | 1:1 | 6 |
| 1536x1024 | 3:2 | 6 |
| 1024x1536 | 2:3 | 6 |
| 941x1672 | 9:16 | 6 |
| 1672x941 | 16:9 | 6 |
| 2048x2048 | 1:1 | 18 |
| 2048x1152 | 16:9 | 18 |
| 1152x2048 | 9:16 | 18 |
| 3840x2160 | 16:9 | 18 |
| 2160x3840 | 9:16 | 18 |
| Custom WxH | Any | 18 |

### Video Models

| Model | 6s | 10s | 15s |
|-------|-----|------|------|
| grok-video-3 | 60 cr | 100 cr | -- |
| grok-video-3-max | 120 cr | 200 cr | 300 cr |

## Aspect Ratios

| Ratio | Image | Video (v3) | Video (v3-max) |
|-------|-------|------------|----------------|
| auto | Yes (pro/2-w) | -- | -- |
| 1:1 | Yes | Yes | -- |
| 16:9 | Yes | Yes | Yes |
| 9:16 | Yes | Yes | Yes |
| 4:3 | Yes | Yes | -- |
| 3:4 | Yes | Yes | -- |
| 3:2 | Yes | Yes | -- |
| 2:3 | Yes | Yes | -- |
| 5:4 | Yes | Yes | -- |
| 4:5 | Yes | Yes | -- |
| 21:9 | Yes | Yes | -- |

## Response Format

### Standard Response (URL-based)

```json
{
  "created": 1234567890,
  "data": [
    {
      "url": "https://...",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  ],
  "usage": {
    "credits_cost": 15,
    "credits_remaining": 985
  }
}
```

### nano-banana-official Response (Base64)

```json
{
  "created": 1234567890,
  "data": [
    {
      "b64_json": "/9j/4AAQ..."
    }
  ],
  "usage": {
    "credits_cost": 10,
    "credits_remaining": 990
  }
}
```

### Async Submit Response

nano-banana-2-w:
```json
{
  "task_id": "a1b2c3d4-xxxx-xxxx",
  "status": "pending"
}
```

gpt-image-2:
```json
{
  "id": "5e9e5ae9-xxxx-xxxx",
  "object": "image.task",
  "status": "processing",
  "creation": 1782959695,
  "model": "gpt-image-2"
}
```

### Poll Response

```json
{
  "status": "processing" | "succeeded" | "failed",
  "data": [...],
  "usage": {...},
  "error": "..." 
}
```

## OpenAI SDK Example (Python)

Sync endpoint (nano-banana-2 / nano-banana-pro only, subject to 300s timeout):

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://xxzapi.coze.site/v1"
)

# Text-to-image (nano-banana-2 or nano-banana-pro)
response = client.images.generate(
    model="nano-banana-2",
    prompt="A serene mountain lake at dawn",
    n=1,
    size="1024x1024"
)
print(response.data[0].url)
```

Async endpoint (recommended for gpt-image-2, 4K, image-to-image):

```python
import requests, time, json

API_KEY = "YOUR_API_KEY"
BASE = "https://xxzapi.coze.site"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Submit
resp = requests.post(f"{BASE}/v1/images/generations/async", headers=HEADERS, json={
    "model": "gpt-image-2",
    "prompt": "A cute orange cat, 4K realistic",
    "size": "2048x2048",
    "n": 1,
    "quality": "high"
}).json()

task_id = resp.get("id") or resp.get("task_id")

# Poll
while True:
    time.sleep(8)
    status = requests.get(f"{BASE}/v1/images/tasks/{task_id}", headers=HEADERS).json()
    if status["status"] == "succeeded":
        print(status["data"][0]["url"])
        break
    elif status["status"] == "failed":
        raise Exception(status.get("error"))
```

## Error Codes

| HTTP | Error Type | Description | Credits |
|------|-----------|-------------|---------|
| 400 | invalid_request_error | Missing or invalid parameters | Not deducted |
| 400 | content_policy_violation | Content moderation block | **Deducted** |
| 401 | authentication_error | Invalid or missing API key | Not deducted |
| 402 | insufficient_credits | Not enough credits | Not deducted |
| 403 | forbidden | Account disabled | -- |
| 429 | rate_limit_error | Over 200 req/min | Not deducted |
| 500 | api_error | Model generation failed | Not deducted |
| 503 | server_error | No generation channel available | Not deducted |
