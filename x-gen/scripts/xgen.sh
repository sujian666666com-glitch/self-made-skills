#!/usr/bin/env bash
# xgen.sh -- Unified CLI wrapper for XXZ API image/video generation
# Usage:
#   xgen.sh image <model> <prompt> [options]
#   xgen.sh video <model> <prompt> [options]
#
# Environment:
#   XXZ_API_KEY  -- required API key
#   XXZ_OUTPUT   -- output directory (default: current dir)
#
# Options:
#   --ratio       Aspect ratio (default: 1:1 for image, 16:9 for video)
#   --size        Image size: 1K/2K/4K (default: 2K)
#   --duration    Video duration in seconds (default: 10)
#   --ref         Reference image URL (can be repeated)
#   --ref-file    Local file path for reference image (base64 encoded)
#   --quality     Image quality: low/medium/high/auto (gpt-image-2 only, default: auto)
#   --count       Number of images to generate (default: 1)
#   --output      Output filename (default: auto-generated)
#   --poll-interval  Seconds between poll requests (default: 10)

set -euo pipefail

BASE_URL="https://xxzapi.coze.site"
API_KEY="${XXZ_API_KEY:-}"
OUTPUT_DIR="${XXZ_OUTPUT:-.}"

if [[ -z "$API_KEY" ]]; then
  echo "Error: XXZ_API_KEY not set. Get your key at https://xxzapi.coze.site" >&2
  exit 1
fi

# --- Helpers ---

auth_header() { echo "Authorization: Bearer $API_KEY"; }

timestamp() { date +%Y%m%d_%H%M%S; }

download_file() {
  local url="$1" dest="$2"
  echo "Downloading: $url -> $dest"
  curl -s -o "$dest" "$url"
  if [[ -f "$dest" ]] && [[ -s "$dest" ]]; then
    echo "Saved: $dest ($(wc -c < "$dest" | tr -d ' ') bytes)"
  else
    echo "Error: Download failed or file is empty" >&2
    return 1
  fi
}

decode_base64_image() {
  local b64="$1" dest="$2"
  echo "$b64" | base64 -d > "$dest"
  if [[ -f "$dest" ]] && [[ -s "$dest" ]]; then
    echo "Saved: $dest ($(wc -c < "$dest" | tr -d ' ') bytes)"
  else
    echo "Error: Base64 decode failed" >&2
    return 1
  fi
}

poll_task() {
  local poll_url="$1" interval="$2" max_attempts="$3"
  local attempt=0
  while (( attempt < max_attempts )); do
    local resp
    resp=$(curl -s -X GET "$poll_url" -H "$(auth_header)")
    local status
    status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    
    case "$status" in
      succeeded)
        echo "Task completed!"
        echo "$resp"
        return 0
        ;;
      failed)
        local err
        err=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','unknown error'))" 2>/dev/null || echo "unknown")
        echo "Task failed: $err" >&2
        echo "$resp"
        return 1
        ;;
      *)
        attempt=$((attempt + 1))
        echo "Status: $status (poll $attempt/$max_attempts), waiting ${interval}s..."
        sleep "$interval"
        ;;
    esac
  done
  echo "Error: Polling timed out after $max_attempts attempts" >&2
  return 1
}

file_to_base64() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "Error: File not found: $file" >&2
    return 1
  fi
  base64 -i "$file" | tr -d '\n'
}

mime_type() {
  local file="$1"
  case "${file##*.}" in
    jpg|jpeg) echo "image/jpeg" ;;
    png) echo "image/png" ;;
    gif) echo "image/gif" ;;
    webp) echo "image/webp" ;;
    *) echo "image/jpeg" ;;
  esac
}

# --- Image Generation ---

gen_image() {
  local model="$1" prompt="$2"
  shift 2
  local ratio="1:1" size="2K" count=1 output="" refs=() ref_files=() quality="auto"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ratio) ratio="$2"; shift 2 ;;
      --size) size="$2"; shift 2 ;;
      --count) count="$2"; shift 2 ;;
      --output) output="$2"; shift 2 ;;
      --ref) refs+=("$2"); shift 2 ;;
      --ref-file) ref_files+=("$2"); shift 2 ;;
      --quality) quality="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  [[ -z "$output" ]] && output="$OUTPUT_DIR/$(timestamp)_${model}.png"

  case "$model" in
    nano-banana-official)
      gen_image_official "$prompt" "$ratio" "$size" "$count" "$output" "${ref_files[@]+"${ref_files[@]}"}"
      ;;
    nano-banana-2-w)
      gen_image_async "$prompt" "$ratio" "$size" "$output" "${refs[@]+"${refs[@]}"}"
      ;;
    gpt-image-2)
      gen_image_gpt_async "$prompt" --ratio "$ratio" --size "$size" --count "$count" --output "$output" --quality "$quality" ${refs[@]+"${refs[@]/#/--ref }"}
      ;;
    nano-banana-2|nano-banana-pro)
      gen_image_sync "$model" "$prompt" "$ratio" "$size" "$count" "$output" "${refs[@]+"${refs[@]}"}"
      ;;
    *)
      echo "Error: Unknown image model: $model" >&2
      exit 1
      ;;
  esac
}

gen_image_sync() {
  local model="$1" prompt="$2" ratio="$3" size="$4" count="$5" output="$6"
  shift 6
  local refs=("$@")

  local body
  body=$(python3 -c "
import json, sys
d = {'model': '$model', 'prompt': '''$prompt''', 'aspectRatio': '$ratio', 'imageSize': '$size', 'n': $count}
refs = sys.argv[1:]
if refs:
    d['images'] = list(refs)
print(json.dumps(d))
" "${refs[@]+"${refs[@]}"}")

  echo "Generating image (sync, $model)..."
  local resp
  resp=$(curl -s -X POST "$BASE_URL/v1/images/generations" \
    -H "$(auth_header)" \
    -H "Content-Type: application/json" \
    -d "$body")

  local url
  url=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('url',''))" 2>/dev/null || echo "")
  
  if [[ -z "$url" ]]; then
    echo "Error: No URL in response" >&2
    echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp" >&2
    return 1
  fi

  download_file "$url" "$output"
  echo "Credits: $(echo "$resp" | python3 -c 'import sys,json;u=json.load(sys.stdin).get("usage",{});print("cost="+str(u.get("credits_cost",0))+", remaining="+str(u.get("credits_remaining",0)))' 2>/dev/null || echo "unknown")"
}

gen_image_official() {
  local prompt="$1" ratio="$2" size="$3" count="$4" output="$5"
  shift 5
  local ref_files=("$@")

  local body
  if [[ ${#ref_files[@]} -gt 0 ]]; then
    local b64_array="" mime_array=""
    for f in "${ref_files[@]}"; do
      [[ -n "$b64_array" ]] && b64_array+="," && mime_array+=","
      b64_array+="\"$(file_to_base64 "$f")\""
      mime_array+="\"$(mime_type "$f")\""
    done
    body=$(python3 -c "
import json
d = {'prompt': '''$prompt''', 'aspectRatio': '$ratio', 'imageSize': '$size', 'n': $count,
     'referenceImages': [$b64_array], 'referenceMimeTypes': [$mime_array]}
print(json.dumps(d))
")
  else
    body=$(python3 -c "
import json
d = {'prompt': '''$prompt''', 'aspectRatio': '$ratio', 'imageSize': '$size', 'n': $count}
print(json.dumps(d))
")
  fi

  echo "Generating image (official, base64)..."
  local resp
  resp=$(curl -s -X POST "$BASE_URL/api/generate/nano-banana-official" \
    -H "$(auth_header)" \
    -H "Content-Type: application/json" \
    -d "$body")

  local b64_data
  b64_data=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('b64_json',''))" 2>/dev/null || echo "")

  if [[ -z "$b64_data" ]]; then
    echo "Error: No base64 data in response" >&2
    echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp" >&2
    return 1
  fi

  decode_base64_image "$b64_data" "$output"
  echo "Credits: $(echo "$resp" | python3 -c 'import sys,json;u=json.load(sys.stdin).get("usage",{});print("cost="+str(u.get("credits_cost",0))+", remaining="+str(u.get("credits_remaining",0)))' 2>/dev/null || echo "unknown")"
}

gen_image_async() {
  local prompt="$1" ratio="$2" size="$3" output="$4"
  shift 4
  local refs=("$@")

  local body
  body=$(python3 -c "
import json, sys
d = {'model': 'nano-banana-2-w', 'prompt': '''$prompt''', 'size': '$size', 'aspectRatio': '$ratio'}
refs = sys.argv[1:]
if refs:
    d['urls'] = list(refs)
print(json.dumps(d))
" "${refs[@]+"${refs[@]}"}")

  echo "Submitting async image task..."
  local resp
  resp=$(curl -s -X POST "$BASE_URL/v1/images/generations/async" \
    -H "$(auth_header)" \
    -H "Content-Type: application/json" \
    -d "$body")

  local task_id
  task_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || echo "")

  if [[ -z "$task_id" ]]; then
    echo "Error: No task_id in response" >&2
    echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp" >&2
    return 1
  fi

  echo "Task ID: $task_id"
  local poll_url="$BASE_URL/v1/images/tasks/$task_id"
  local result
  result=$(poll_task "$poll_url" 8 60)

  local url
  url=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('url',''))" 2>/dev/null || echo "")

  if [[ -n "$url" ]]; then
    download_file "$url" "$output"
  fi
}

# --- GPT-Image-2 (Async, pixel-based sizes) ---

map_gpt_image_size() {
  local size="$1" ratio="$2"
  # Pass through custom WxH format
  if [[ "$size" =~ ^[0-9]+x[0-9]+$ ]]; then
    echo "$size"
    return
  fi
  case "$size" in
    1K)
      case "$ratio" in
        1:1)   echo "1024x1024" ;;
        3:2)   echo "1536x1024" ;;
        2:3)   echo "1024x1536" ;;
        16:9)  echo "1672x941" ;;
        9:16)  echo "941x1672" ;;
        *)     echo "1024x1024" ;;
      esac
      ;;
    2K)
      case "$ratio" in
        1:1)   echo "2048x2048" ;;
        16:9)  echo "2048x1152" ;;
        9:16)  echo "1152x2048" ;;
        *)     echo "2048x2048" ;;
      esac
      ;;
    4K)
      case "$ratio" in
        16:9)  echo "3840x2160" ;;
        9:16)  echo "2160x3840" ;;
        1:1)   echo "3840x3840" ;;
        *)     echo "3840x2160" ;;
      esac
      ;;
    *) echo "1024x1024" ;;
  esac
}

gen_image_gpt_async() {
  local prompt="$1"
  shift
  local ratio="1:1" size="2K" count=1 output="" quality="auto" refs=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ratio) ratio="$2"; shift 2 ;;
      --size) size="$2"; shift 2 ;;
      --count) count="$2"; shift 2 ;;
      --output) output="$2"; shift 2 ;;
      --quality) quality="$2"; shift 2 ;;
      --ref) refs+=("$2"); shift 2 ;;
      *) shift ;;
    esac
  done

  [[ -z "$output" ]] && output="$OUTPUT_DIR/$(timestamp)_gpt-image-2.png"

  local pixel_size
  pixel_size=$(map_gpt_image_size "$size" "$ratio")

  local body
  body=$(python3 -c "
import json, sys
d = {'model': 'gpt-image-2', 'prompt': '''$prompt''', 'size': '$pixel_size', 'n': $count, 'quality': '$quality'}
refs = sys.argv[1:]
if refs:
    d['images'] = list(refs)
print(json.dumps(d))
" "${refs[@]+"${refs[@]}"}")

  echo "Submitting async image task (gpt-image-2, $pixel_size, quality=$quality)..."
  local resp
  resp=$(curl -s -X POST "$BASE_URL/v1/images/generations/async" \
    -H "$(auth_header)" \
    -H "Content-Type: application/json" \
    -d "$body")

  local task_id
  task_id=$(echo "$resp" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('id', d.get('task_id', '')))
" 2>/dev/null || echo "")

  if [[ -z "$task_id" ]]; then
    echo "Error: No task_id in response" >&2
    echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp" >&2
    return 1
  fi

  echo "Task ID: $task_id"
  local poll_url="$BASE_URL/v1/images/tasks/$task_id"
  local result
  result=$(poll_task "$poll_url" 8 60)

  # gpt-image-2 response format varies: data[], result string, or result.images[]
  local url
  url=$(echo "$result" | python3 -c "
import sys,json
d=json.load(sys.stdin)
# Standard data field
if 'data' in d and d['data']:
    print(d['data'][0].get('url',''))
elif 'result' in d:
    r = d['result']
    if isinstance(r, str):
        r = json.loads(r)
    # result as list
    if isinstance(r, list):
        print(r[0].get('url','') if r else '')
    # result as dict with images key
    elif isinstance(r, dict):
        imgs = r.get('images', r.get('data', []))
        print(imgs[0].get('url','') if imgs else '')
    else:
        print('')
else:
    print('')
" 2>/dev/null || echo "")

  if [[ -n "$url" ]]; then
    download_file "$url" "$output"
    echo "Credits: $(echo "$result" | python3 -c '
import sys,json
d=json.load(sys.stdin)
cost=d.get("credits_cost", d.get("usage",{}).get("credits_cost",0))
remain=d.get("credits_remaining", d.get("usage",{}).get("credits_remaining","?"))
print("cost="+str(cost)+", remaining="+str(remain))
' 2>/dev/null || echo "unknown")"
  fi
}

# --- Video Generation ---

gen_video() {
  local model="$1" prompt="$2"
  shift 2
  local ratio="16:9" duration=10 output="" refs=() poll_interval=15

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ratio) ratio="$2"; shift 2 ;;
      --duration) duration="$2"; shift 2 ;;
      --output) output="$2"; shift 2 ;;
      --ref) refs+=("$2"); shift 2 ;;
      --poll-interval) poll_interval="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  [[ -z "$output" ]] && output="$OUTPUT_DIR/$(timestamp)_${model}.mp4"

  local body
  body=$(python3 -c "
import json, sys
d = {'model': '$model', 'prompt': '''$prompt''', 'duration': $duration, 'aspectRatio': '$ratio'}
refs = sys.argv[1:]
if refs:
    d['image_urls'] = list(refs)
print(json.dumps(d))
" "${refs[@]+"${refs[@]}"}")

  echo "Submitting video task ($model, ${duration}s, $ratio)..."
  local resp
  resp=$(curl -s -X POST "$BASE_URL/api/generate/video-async" \
    -H "$(auth_header)" \
    -H "Content-Type: application/json" \
    -d "$body")

  local task_id
  task_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id', json.load(open('/dev/stdin')).get('task_id','')))" 2>/dev/null || echo "")

  # Fallback: try parsing id or task_id
  if [[ -z "$task_id" ]]; then
    task_id=$(echo "$resp" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('id', d.get('task_id', '')))
" 2>/dev/null || echo "")
  fi

  if [[ -z "$task_id" ]]; then
    echo "Error: No task ID in response" >&2
    echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp" >&2
    return 1
  fi

  echo "Task ID: $task_id"
  local poll_url="$BASE_URL/api/generate/video-async/poll/$task_id"
  
  # Video takes longer, more poll attempts
  local max_attempts=60
  if (( duration > 6 )); then
    max_attempts=90
  fi

  local result
  result=$(poll_task "$poll_url" "$poll_interval" "$max_attempts")

  local url
  url=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('url',''))" 2>/dev/null || echo "")

  if [[ -n "$url" ]]; then
    download_file "$url" "$output"
    echo "Credits: $(echo "$result" | python3 -c 'import sys,json;u=json.load(sys.stdin).get("usage",{});print("cost="+str(u.get("credits_cost",0))+", remaining="+str(u.get("credits_remaining",0)))' 2>/dev/null || echo "unknown")"
  fi
}

# --- Main ---

usage() {
  cat <<'USAGE'
X-GEN CLI -- XXZ API Image & Video Generation

Usage:
  xgen.sh image <model> <prompt> [options]
  xgen.sh video <model> <prompt> [options]

Image models: nano-banana-2, nano-banana-pro, nano-banana-official, nano-banana-2-w, gpt-image-2
Video models: grok-video-3, grok-video-3-max

Options:
  --ratio <ratio>       Aspect ratio (1:1, 16:9, 9:16, etc.)
  --size <size>         Image size: 1K/2K/4K or WxH for gpt-image-2 (e.g. 1920x1080)
  --duration <sec>      Video duration (default: 10)
  --ref <url>           Reference image URL (repeatable)
  --ref-file <path>     Local reference image file
  --quality <level>     Quality: low/medium/high/auto (gpt-image-2 only)
  --count <n>           Number of images (default: 1)
  --output <path>       Output filename
  --poll-interval <sec> Poll interval for async tasks (default: 10/15)

Notes:
  gpt-image-2 uses async endpoint by default (avoids 300s gateway timeout).
  gpt-image-2 size supports: 1K/2K/4K (mapped to pixels) or custom WxH (max 3840px).

Environment:
  XXZ_API_KEY           API key (required)
  XXZ_OUTPUT            Output directory (default: .)

Examples:
  xgen.sh image nano-banana-2 "A cat in sunshine" --ratio 1:1 --size 2K
  xgen.sh image nano-banana-pro "Watercolor landscape" --ratio 16:9 --size 4K
  xgen.sh image nano-banana-official "Cyberpunk city" --ref-file photo.jpg
  xgen.sh image gpt-image-2 "A cute cat, 4K realistic" --size 2K --ratio 16:9 --quality high
  xgen.sh image gpt-image-2 "Van Gogh style" --ref https://img.jpg --size 1024x1024
  xgen.sh image gpt-image-2 "Wide banner" --size 3840x2160
  xgen.sh video grok-video-3 "Ocean sunset timelapse" --duration 10 --ratio 16:9
  xgen.sh video grok-video-3-max "Person turns around" --ref https://img.jpg --duration 15
USAGE
}

if [[ $# -lt 3 ]]; then
  usage
  exit 1
fi

cmd="$1"; shift
model="$1"; shift
prompt="$1"; shift

case "$cmd" in
  image) gen_image "$model" "$prompt" "$@" ;;
  video) gen_video "$model" "$prompt" "$@" ;;
  *)     usage; exit 1 ;;
esac
