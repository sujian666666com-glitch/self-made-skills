---
name: x-gen
description: "Generate images and videos via XXZ API (xxzapi.coze.site). Covers text-to-image, image-to-image, text-to-video, and image-to-video with models: gpt-image-2, nano-banana-2, nano-banana-pro, nano-banana-official, nano-banana-2-w, grok-video-3, grok-video-3-max. Use when the user asks to generate, create, or produce images or videos, mentions AI art, AI drawing, text-to-image, image-to-image, style transfer, text-to-video, image-to-video, or names any of the supported models."
version: 1.0.0
---

# X-GEN: Image & Video Generation

Generate images and videos via XXZ API. All models share Bearer token auth and a common response schema.

## Prerequisites

Environment variable `XXZ_API_KEY` must be set. If missing, tell the user:
> Please set your API key: `export XXZ_API_KEY="your-key"` (get one at https://xxzapi.coze.site)

Base URL: `https://xxzapi.coze.site`
Auth header: `Authorization: Bearer $XXZ_API_KEY`
Rate limit: 200 req/min. Generated URLs expire in **2 hours** -- always download results.

## Model Selection

Pick the best model for the user's need:

| Model | Best For | Cost | Type | Flow |
|-------|----------|------|------|------|
| nano-banana-2 | General images, budget-friendly | 10-15 cr | Image | Sync |
| nano-banana-pro | High quality, auto aspect ratio | 20-30 cr | Image | Sync |
| nano-banana-official | Gemini 3.1 Flash, base64 output, multi-ref | 10-15 cr | Image | Sync |
| nano-banana-2-w | Reference image workflow, 4K | 15 cr | Image | Async |
| gpt-image-2 | OpenAI image gen, custom sizes, image-to-image, quality control | 6-18 cr | Image | Async |
| grok-video-3 | Text-to-video + image-to-video, all ratios | 60-100 cr | Video | Async |
| grok-video-3-max | Image-to-video only, higher quality | 120-300 cr | Video | Async |

**Decision logic:**
- Casual / fast image -> `nano-banana-2`
- Professional quality / auto ratio -> `nano-banana-pro`
- Need base64 or multiple reference images -> `nano-banana-official`
- Need reference image with 4K -> `nano-banana-2-w`
- Custom pixel sizes, quality control, or image-to-image with OpenAI model -> `gpt-image-2` (async, avoids 300s gateway timeout)
- Text-to-video -> `grok-video-3`
- Image-to-video (higher quality) -> `grok-video-3-max`
- If user names a specific model, use that model directly

**Async recommendation:** For image-to-image, 4K, or custom sizes, prefer async endpoints to avoid the 300-second gateway timeout on sync calls.

## Image Generation

### Sync Models (nano-banana-2, nano-banana-pro)

Endpoint: `POST /v1/images/generations`

```bash
curl -s -X POST https://xxzapi.coze.site/v1/images/generations \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-2",
    "prompt": "PROMPT",
    "aspectRatio": "16:9",
    "imageSize": "2K",
    "n": 1
  }'
```

Parameters: `prompt` (required), `aspectRatio`, `imageSize` (1K/2K/4K), `n` (count), `images` (URL array for image-to-image).

For image-to-image, add `"images": ["https://..."]` and optionally `"aspectRatio": "auto"` (pro only) to preserve original ratio.

### Sync Model -- nano-banana-official (Base64 workflow)

Endpoint: `POST /api/generate/nano-banana-official`

This model returns **Base64 image data** in the response (not URLs). Requires different handling.

Text-to-image:
```bash
curl -s -X POST https://xxzapi.coze.site/api/generate/nano-banana-official \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "PROMPT",
    "aspectRatio": "1:1",
    "imageSize": "2K",
    "n": 1
  }'
```

Image-to-image (reference images as Base64):
```bash
# 1. Convert local image to base64
BASE64=$(base64 -i input.jpg | tr -d '\n')

# 2. Send request
curl -s -X POST https://xxzapi.coze.site/api/generate/nano-banana-official \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"PROMPT\",
    \"aspectRatio\": \"1:1\",
    \"imageSize\": \"2K\",
    \"n\": 1,
    \"referenceImages\": [\"$BASE64\"],
    \"referenceMimeTypes\": [\"image/jpeg\"]
  }"
```

After receiving Base64 response, decode and save:
```bash
# Response contains data[].b64_json -- decode it
echo "$B64_JSON" | base64 -d > output.png
```

Parameters: `prompt` (required), `aspectRatio` (default 1:1), `imageSize` (1K/2K/4K), `n` (1-4), `referenceImages` (base64 array), `referenceMimeTypes` (MIME types).

In prompts, use "image 1", "image 2" to reference multiple input images.

### Async Model -- nano-banana-2-w

Endpoint: `POST /v1/images/generations/async` (submit) + `GET /v1/images/tasks/{task_id}` (poll)

Step 1 -- Submit:
```bash
curl -s -X POST https://xxzapi.coze.site/v1/images/generations/async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-2-w",
    "prompt": "PROMPT",
    "size": "1K"
  }'
```

Step 2 -- Poll (every 5-10s):
```bash
curl -s -X GET "https://xxzapi.coze.site/v1/images/tasks/{task_id}" \
  -H "Authorization: Bearer $XXZ_API_KEY"
```

**Note:** The sync endpoint `/v1/images/generations` returns 503 for this model -- async only.

Parameters differ from sync models: use `size` (not `imageSize`), use `urls` (not `images`) for reference images. Supports `aspectRatio` with `auto` default.

### Async Model -- gpt-image-2 (Pixel-based sizes, quality control)

Endpoint: `POST /v1/images/generations/async` (submit) + `GET /v1/images/tasks/{task_id}` (poll)

**Recommended to use async by default** -- sync endpoint is subject to a 300-second gateway timeout which often fails for large or complex images.

Text-to-image:
```bash
curl -s -X POST https://xxzapi.coze.site/v1/images/generations/async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A cute orange cat napping in sunlight, 4K realistic",
    "size": "2048x2048",
    "n": 1,
    "quality": "high"
  }'
```

Image-to-image (URL or base64 reference):
```bash
curl -s -X POST https://xxzapi.coze.site/v1/images/generations/async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "Transform into Van Gogh style",
    "size": "1024x1024",
    "images": ["https://example.com/photo.jpg"]
  }'
```

Custom pixel size (e.g. wide banner):
```bash
curl -s -X POST https://xxzapi.coze.site/v1/images/generations/async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A cute orange cat",
    "size": "3840x2160",
    "n": 1
  }'
```

Poll for result (every 5-10s):
```bash
curl -s -X GET "https://xxzapi.coze.site/v1/images/tasks/{task_id}" \
  -H "Authorization: Bearer $XXZ_API_KEY"
```

Parameters: `prompt` (required), `size` (pixel format, default `1024x1024`), `n` (1-10), `quality` (`low`/`medium`/`high`/`auto`), `images` (URL or base64 array for image-to-image), `mask` (PNG file for inpainting, transparent area = edit region).

Custom sizes: any WxH where max side <= 3840px and both dimensions are multiples of 16. Custom sizes cost 18 cr/image.

## Video Generation

All video models are **async**. Submit task, then poll for result.

### Step 1 -- Submit Task

Endpoint: `POST /api/generate/video-async`

Text-to-video (grok-video-3 only):
```bash
curl -s -X POST https://xxzapi.coze.site/api/generate/video-async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-video-3",
    "prompt": "PROMPT",
    "duration": 10,
    "aspectRatio": "16:9"
  }'
```

Image-to-video (both models; **required** for grok-video-3-max):
```bash
curl -s -X POST https://xxzapi.coze.site/api/generate/video-async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-video-3-max",
    "prompt": "PROMPT",
    "duration": 15,
    "aspectRatio": "9:16",
    "image_urls": ["https://example.com/photo.jpg"]
  }'
```

### Step 2 -- Poll for Result

Endpoint: `GET /api/generate/video-async/poll/{id}`

```bash
curl -s -X GET "https://xxzapi.coze.site/api/generate/video-async/poll/{task_id}" \
  -H "Authorization: Bearer $XXZ_API_KEY"
```

Status values: `processing` / `succeeded` / `failed`.
Typical wait: 6s video ~1-3 min, 10-15s video ~3-8 min. Poll every 15-20s.

### Video Constraints

| | grok-video-3 | grok-video-3-max |
|--|-------------|-----------------|
| Text-to-video | Yes | No (image_urls required) |
| Image-to-video | Yes | Yes |
| Aspect ratios | All | 9:16, 16:9 only |
| Duration | 6s (60cr), 10s (100cr) | 6s (120cr), 10s (200cr), 15s (300cr) |

## Post-Generation: Download Results

Generated URLs expire in 2 hours. Always download immediately:

```bash
curl -s -o output.png "RESULT_URL"
```

Use `scripts/xgen.sh` for the full workflow (submit + poll + download). See [scripts/README.md](scripts/README.md).

## Aspect Ratios

Image models: `auto`, `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `5:4`, `4:5`, `21:9`.
Video grok-video-3: all ratios. Video grok-video-3-max: `9:16`, `16:9` only.

## Response Schema

All endpoints share this response shape:

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

`duration` and `aspect_ratio` only appear for video models. `nano-banana-official` returns `b64_json` instead of `url`.

## Error Handling

| Code | Error | Action |
|------|-------|--------|
| 400 | invalid_request_error | Check parameters |
| 400 | content_policy_violation | Content blocked, credits deducted |
| 401 | authentication_error | Check API key |
| 402 | insufficient_credits | Top up credits |
| 429 | rate_limit_error | Wait, max 200 req/min |
| 500 | api_error | Model generation failed, retry |
| 503 | server_error | No channel available, retry later |

## Additional Resources

For complete parameter reference and SDK examples, see [api-reference.md](api-reference.md).
