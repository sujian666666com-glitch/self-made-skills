# x-gen 图片生成：当前状态与正确用法

> 实测时间：2026-07-02。本文件由真实调用校准，数值均为实测值，非文档默认值。
> 所有命令需先 `export XXZ_API_KEY="your_key"`。Base URL：`https://xxzapi.coze.site`。

---

## 当前后端状态表（实测）

| 模型 | 端点 | 状态 | 延迟 | 积分/张 | 备注 |
|------|------|------|------|---------|------|
| **gpt-image-2** | **sync** `/v1/images/generations` | ✅ **可用（推荐）** | 30-100s | **6** | 1K/2K、各比例、长短 prompt 均实测通过。画质好、积分低、最稳 |
| nano-banana-2 | sync `/v1/images/generations` | ✅ 可用 | ~40s | 15 | 画质一般，适合快速验证 prompt 效果 |
| nano-banana-pro | sync `/v1/images/generations` | ⚠️ 不稳定 | 2-5min 或挂死 | 20 | 同步网关 ~2min 会断连，偶尔成功，不建议 |
| nano-banana-2-w | async `/v1/images/generations/async` | ❌ **挂了** | — | — | 后端持续返回 `google gemini timeout`，连最简 prompt 也在 ~90s 超时 |
| nano-banana-official | sync `/api/generate/nano-banana-official` | ❌ 401 | — | — | 当前 key 无权限，`{"error":"未登录"}`，不要尝试 |
| grok-video-3 / -max | async | 未测 | — | — | 视频模型，本文档不覆盖 |

**结论：默认用 `gpt-image-2`（sync）。** 它是目前唯一画质好、积分低、稳定可用的图像模型。

---

## 方案 A（推荐）：gpt-image-2 sync 文生图

最稳的路径。一条 curl 出图，无需轮询。

```bash
# 写 JSON 到文件（避免 shell 引号问题，长 prompt 必须这样做）
cat > /tmp/gen.json <<'EOF'
{
  "model": "gpt-image-2",
  "prompt": "Women ivory off-white mini dress with small black polka dots, square neckline, wide shoulder straps, sleeveless, fitted waist, flared A-line skirt, on clean white studio background, full garment visible, premium product photo",
  "aspectRatio": "16:9",
  "imageSize": "2K",
  "n": 1
}
EOF

curl -s --max-time 280 -X POST https://xxzapi.coze.site/v1/images/generations \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/gen.json -o /tmp/resp.json

# 取 URL 并下载
URL=$(python3 -c "import json;print(json.load(open('/tmp/resp.json'))['data'][0]['url'])")
curl -s -o ./output.png "$URL"
```

- **延迟**：30-100s（长 prompt + 2K 偏慢，但不会超过 280s）
- **积分**：6 cr/张（1K/2K 同价）
- **响应**：`data[0].url` 是公网图片地址，**2 小时后过期，必须立即下载**
- 用脚本：`bash scripts/xgen.sh image gpt-image-2 "prompt..." --size 2K --ratio 16:9 --output ./out.png`

---

## 方案 B：nano-banana-2 sync 快速验证

画质不如 gpt-image-2，但快，适合先看 prompt 效果再决定要不要出高质量版。

```bash
bash scripts/xgen.sh image nano-banana-2 \
  "fashion product photo, polka dot dress, studio lighting" \
  --ratio 1:1 --size 1K \
  --output ./draft.png
```

- 延迟 ~40s，15 cr/张
- 验证满意后，用方案 A 出正式版

---

## 方案 C：图生图（gpt-image-2 + 参考图）

`gpt-image-2` 支持 `images` 字段传**公网 URL** 做参考图（用于 product identity lock）。

```bash
cat > /tmp/gen.json <<'EOF'
{
  "model": "gpt-image-2",
  "prompt": "Transform the reference garment into a clean studio product photo, white background, full garment visible",
  "aspectRatio": "1:1",
  "imageSize": "2K",
  "n": 1,
  "images": ["https://your-public-url.com/ref.png"]
}
EOF
curl -s --max-time 280 -X POST https://xxzapi.coze.site/v1/images/generations \
  -H "Authorization: Bearer $XXZ_API_KEY" -H "Content-Type: application/json" \
  -d @/tmp/gen.json -o /tmp/resp.json
```

⚠️ **参考图 URL 注意事项（实测踩坑）：**
- 后端从 `tmpfiles.org` 拉图**不稳定**：本地能拉到真实 PNG（`/dl/` 变体），但 gpt-image-2 后端经常报 `image upload failed, please check the image`。偶尔成功，不可靠。
- base64 data-URI（`data:image/png;base64,...`）实测会让请求挂死，**不要用**。
- **可靠做法**：若没有稳定公网图床，直接走方案 A 文生图，把产品身份写进 prompt 的详细文字描述里（gpt-image-2 纯文字生成稳定）。

---

## gpt-image-2 尺寸 / 积分速查

| imageSize + aspectRatio | 出图尺寸（约） | 积分 |
|-------------------------|----------------|------|
| 1K + 1:1 | 1024×1024 | **6** |
| 1K + 16:9 | ~1672×941 | **6** |
| 1K + 3:4 | 1024×1536 | **6** |
| 2K + 1:1 | 2048×2048 | **6** |
| 2K + 16:9 | ~2048×1152 | **6** |

> 关键：**1K 和 2K 积分相同，都是 6 cr/张**（实测，非文档默认的 18cr）。要高清直接上 2K。
> 支持比例：`auto / 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 / 5:4 / 4:5 / 21:9`。

---

## gpt-image-2 异步手动流程（提交 → 轮询 → 下载）

> 注意：`gpt-image-2` 本身走 **sync** 就够（见方案 A）。异步端点 `/v1/images/generations/async` 实际服务于 `nano-banana-2-w`（当前挂了）。下方为通用异步手动流程，留作后端恢复或特殊长任务时使用。

```bash
# 1. 提交任务
curl -s -X POST https://xxzapi.coze.site/v1/images/generations/async \
  -H "Authorization: Bearer $XXZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"nano-banana-2-w","prompt":"...","size":"2K","aspectRatio":"16:9","urls":["https://ref.png"]}'
# 返回 {"id":"<task_id>","status":"processing", ...}  ← 注意取 id 字段（不是 task_id）

# 2. 轮询（每 10s）
curl -s "https://xxzapi.coze.site/v1/images/tasks/<task_id>" \
  -H "Authorization: Bearer $XXZ_API_KEY"
# status: processing → succeeded（取 data[0].url）/ failed（看 error）

# 3. 下载（URL 2 小时过期）
curl -s -o ./out.png "<result_url>"
```

---

## 常见错误对照表

| 现象 | 原因 | 处理 |
|------|------|------|
| `HTTP 000` / curl `rc=28` | 连接挂死或超过 `--max-time` | gpt-image-2 sync 把 `--max-time` 设到 280；批量时串行跑（并发会触发后端排队卡死） |
| `image upload failed, please check the image` | gpt-image-2 后端拉不到参考图 URL（tmpfiles 尤其不稳） | 换稳定图床，或改走文生图（方案 A） |
| `{"error":"未登录"}` 401 | 当前 key 对该端点无权限（nano-banana-official） | 换 gpt-image-2 |
| `google gemini timeout` | nano-banana-2-w 后端超时（当前持续故障） | 弃用 2-w，改 gpt-image-2 |
| `余额不足，请充值` | credits 不足 | `credits_remaining` 见每次响应的 `usage` 字段 |
| `content_policy_violation` | 内容审核拦截 | 改 prompt，积分已扣不退 |
| 批量并发全 rc=28 | 多个 2K 请求同时打触发后端排队 | **串行**跑，每张之间 `sleep 5` |

---

## 批量出图推荐脚本

**核心原则：串行，不要并发**（实测 5 个 2K 并发会让每个都卡到超时）。每张 sleep 5s 避免限流（200 req/min）。

```bash
#!/usr/bin/env bash
set -e
mkdir -p ./raw
PROMPTS_DIR="./prompts"   # 每个文件是一段 prompt
for pf in "$PROMPTS_DIR"/*.txt; do
  name=$(basename "$pf" .txt)
  python3 -c "
import json
print(json.dumps({
  'model':'gpt-image-2',
  'prompt':open('$pf').read().strip(),
  'aspectRatio':'16:9','imageSize':'2K','n':1
}))" > /tmp/_body.json
  curl -s --max-time 280 -X POST https://xxzapi.coze.site/v1/images/generations \
    -H "Authorization: Bearer $XXZ_API_KEY" -H "Content-Type: application/json" \
    -d @/tmp/_body.json -o /tmp/_resp.json
  URL=$(python3 -c "import json;print(json.load(open('/tmp/_resp.json'))['data'][0]['url'])")
  curl -s -o "./raw/${name}.png" "$URL"
  echo "✅ $name -> ./raw/${name}.png"
  sleep 5
done
```

- 5 张 2K 串行约需 4-8 分钟（每张 30-100s）
- 每张 6 cr，5 张共 30 cr
- 挂死的单张：记下 prompt，跳过继续，最后单独重试
