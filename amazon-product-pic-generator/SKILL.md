---
name: amazon-product-pic-generator
description: >
  Generate Amazon Listing image packages from product photos. Use when the user wants to
  create Amazon product listing images (hero/main image, feature infographic, lifestyle,
  in-use, close-up, dimension/scale, comparison, packaging/brand trust images) from one
  or more product raw photos. Also triggers for requests like "生成亚马逊产品图",
  "amazon listing images", "产品主图", "亚马逊白底图", "电商产品图生成".
---

# Amazon Product Picture Generator

Generate 2000×2000 Amazon Listing image sets from product photos via `og-image2` API.

## Quick Start

```bash
# Single image
python3 script/generate.py -p "Amazon white background hero shot, minimalist product photography" -o ./output/ --prefix hero

# Batch from JSON (concurrent)
python3 script/batch_generate.py --tasks tasks.json -o ./output/
```

## Image Types Supported

| Type | Key | Description |
|------|-----|-------------|
| Hero | `hero` | White bg, no text, product 85%+ coverage |
| Infographic | `infographic` | Feature callouts, arrows, annotations |
| Lifestyle | `lifestyle` | Product in real-life scene |
| In-Use | `in_use` | Product being held/operated |
| Close-Up | `closeup` | Material, texture, details |
| Dimension | `dimension` | Size/scale annotations |
| Comparison | `comparison` | Structured comparison table |
| Packaging | `packaging` | Package, accessories, brand trust |

## Workflow

1. **Gather inputs**: product image(s), category, key selling points, specs
2. **Build task JSON**: one entry per image type, with tailored prompts
3. **Run batch_generate.py**: concurrent generation, downloads all images
4. **Review & deliver**: output directory contains labeled JPGs + metadata JSON

See `references/image-prompts.md` for prompt templates per image type.
See `references/tasks-example.json` for a complete task JSON example.

## Scripts

### generate.py (single image)

```bash
python3 script/generate.py \
  --prompt "你的提示词" \
  --model og-image2-low \
  --size 2000x2000 \
  --n 1 \
  --output ./output/ \
  --prefix hero
```

### batch_generate.py (concurrent batch)

Accepts a JSON task file:

```json
{
  "product_name": "GreenOnion Food Storage",
  "product_images": ["./input/product.jpg"],
  "category": "Kitchen & Dining",
  "selling_points": ["BPA-free", "Airtight seal", "Stackable"],
  "tasks": [
    {"type": "hero", "prompt": "White background product shot...", "prefix": "01_hero"},
    {"type": "infographic", "prompt": "Infographic showing...", "prefix": "02_infographic"}
  ]
}
```

```bash
python3 script/batch_generate.py --tasks tasks.json -o ./output/ --concurrency 4
```

Output:
- `output/01_hero.jpg`, `output/02_infographic.jpg`, etc.
- `output/metadata.json` — all prompts, URLs, file paths for traceability

## API Configuration

Set in `script/.env` or environment variables:

```
OG_IMAGE2_API_KEY=sk-xxx
OG_IMAGE2_API_URL=http://10.0.0.97:8081/v1
OG_IMAGE2_MODEL=og-image2-low
```

## Amazon Compliance Notes

- **Hero image**: Pure white bg (RGB 255,255,255), no text/logo/props/borders, product ≥ 85% frame
- **Auxiliary images**: Text/graphics allowed, must not mislead or use unverified claims
- **All images**: Square 2000×2000 recommended, JPG format, RGB color space

## Dependencies

```bash
pip install requests python-dotenv
```
