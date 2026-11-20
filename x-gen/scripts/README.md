# X-GEN Scripts

Utility scripts for the X-GEN skill.

## xgen.sh

Unified CLI wrapper that handles the full workflow: submit task, poll for results, and download output files.

### Setup

```bash
chmod +x scripts/xgen.sh
export XXZ_API_KEY="your-api-key"
```

### Usage

**Text-to-image:**
```bash
./scripts/xgen.sh image nano-banana-2 "A serene mountain lake" --ratio 16:9 --size 2K
```

**Image-to-image (URL reference):**
```bash
./scripts/xgen.sh image nano-banana-pro "Convert to watercolor" --ref "https://example.com/photo.jpg" --ratio auto
```

**Image-to-image (local file, nano-banana-official):**
```bash
./scripts/xgen.sh image nano-banana-official "Make it a painting" --ref-file ./photo.jpg --size 4K
```

**Text-to-image (gpt-image-2, async):**
```bash
./scripts/xgen.sh image gpt-image-2 "A cute orange cat, 4K realistic" --size 2K --ratio 16:9 --quality high
```

**Image-to-image (gpt-image-2):**
```bash
./scripts/xgen.sh image gpt-image-2 "Transform into Van Gogh style" --ref https://example.com/photo.jpg --size 1024x1024
```

**Custom pixel size (gpt-image-2):**
```bash
./scripts/xgen.sh image gpt-image-2 "Wide banner scene" --size 3840x2160
```

**Text-to-video:**
```bash
./scripts/xgen.sh video grok-video-3 "Sunset over the ocean" --duration 10 --ratio 16:9
```

**Image-to-video:**
```bash
./scripts/xgen.sh video grok-video-3-max "Person slowly turns" --ref "https://example.com/photo.jpg" --duration 15 --ratio 9:16
```

### Environment Variables

- `XXZ_API_KEY` (required): Your XXZ API key
- `XXZ_OUTPUT` (optional): Output directory, defaults to current directory
