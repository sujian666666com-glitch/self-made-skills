# Amazon A+ 长图生成规范

## 定位

`amazon-a-plus-graph` 默认产出按 Amazon A+ 标准结构打造的电商长图（宽 750px），按 `profile` 决定段数：

- **默认 profile** `a-plus-standard-12`：12 模块完整 A+ 叙事，适合高客单与品牌化。
- **简化 profile** `a-plus-lite-8`：8 段日常出图，节省 API 成本。
- **兼容 profile** `legacy-long-7`：旧通用 7 段长图，向后兼容旧调用与旧 `detail-plan.json`。
- **单模块 profile** `single-modules`：Amazon Basic A+ `970x300`、Premium A+ `1464x600`、Brand Story `1500x500` 工作稿。

视觉系统按 10 大品类（`tech / food / wellness / pet / home / beauty / outdoor / baby / apparel / tools`）自适应，详见 `amazon-aplus-style-system.md` 与 `category-profiles.json`。

## 输入与事实边界

用户必须提供：

- 商品图：正面、斜侧面、实拍、包装图均可。
- 商品名称。

用户可选提供：

- 品牌名、卖点、规格、成分、容量、型号、产地、认证、同系列 SKU、目标人群、目标市场、目标风格。

事实规则：

- 视觉素材可以生成。
- 精确事实不能编造：营养成分、配料、认证、容量、适配范围、功效数字、奖项、产地等必须来自用户提供或可靠来源。
- 信息缺失时使用泛化视觉表达，并写入 `review_required` 与 `assumptions_used`。

## Schema：`buyer-reason-card.json`

```json
{
  "target_buyer": "谁在买，使用场景",
  "purchase_trigger": "为什么现在会考虑买",
  "belief_shift": "图片要让用户从旧认知转到新认知",
  "primary_selling_reason": "唯一主购买理由",
  "proof_material": "已有证据或 proof placeholder",
  "review_recommendation_material": "真实评价 / 推荐 / 主题，按 Switch 决定",
  "offer_lever": "价格 / 组合 / 保障 / 物流 / 赠品 / 低风险承诺",
  "evidence_bound_claims": ["数据 / 认证 / 销量 / 真实评价 / 品牌授权，仅在有证据时使用"],
  "source_labels": {
    "target_buyer": "User-provided",
    "purchase_trigger": "Inferred",
    "primary_selling_reason": "User-provided",
    "evidence_bound_claims": "Web-researched"
  }
}
```

## Schema：`style-lock.json`

```json
{
  "visual_direction": "premium tech ecommerce",
  "palette": ["#f5f6f8", "#1f2933", "#0f1c2e", "#3b6cf6"],
  "accent": "#39ff8a",
  "temperature": "cool",
  "font_system": "modern geometric sans-serif headline placeholders only",
  "background_system": "minimal studio with subtle category cues",
  "lighting_system": "neutral-cool studio lighting with crisp specular highlights",
  "layout_system": "rounded info cards, generous whitespace, consistent label hierarchy",
  "icon_system": "thin-line consistent stroke icons",
  "product_presentation": "stable scale and placement, premium product photography",
  "consistency_requirements": "fixed palette, single font system, stable backgrounds, consistent lighting, matched icon styles",
  "summary": "Campaign Style Lock: consistent premium Amazon A+ visual system across all sections; fixed palette ...; rounded info cards; thin-line icons; clean studio lighting; stable product scale and placement; generous whitespace.",
  "summary_hash": "sha1 / md5 of summary"
}
```

每段 Prompt 必须复用同一段 `style_lock.summary`。`manifest.json` 记录 `style_lock_hash`，便于发现段间被污染。

## Schema：`research.json`

```json
{
  "product_name": "商品名称",
  "brand": "品牌名",
  "verified_facts": [
    { "claim": "已确认事实", "source_url": "https://example.com", "usage": "可用于图文", "source_label": "Web-researched" }
  ],
  "probable_claims": [
    { "claim": "可能成立但需要复核", "reason": "来源不够权威或信息不完整", "source_label": "Inferred" }
  ],
  "missing_facts": ["缺失的规格、认证、成分等"],
  "risk_notes": ["需要人工复核的合规风险"]
}
```

## Schema：`detail-plan.json`

```json
{
  "product_name": "商品名称",
  "profile": "a-plus-standard-12",
  "category": "wellness",
  "product_type_template": "pet-travel-hydration",
  "product_type_narrative": {
    "label": "Pet travel hydration bottle",
    "narrative_core": "Outdoor thirst solved in one hand",
    "shopper_tension": "Pet owners need fast hydration outdoors without carrying a separate bowl",
    "visual_principles": ["Each section has a distinct selling job"]
  },
  "conversion_driver": "pain",
  "english_baseline": true,
  "canvas": { "width": 750, "style": "Amazon A+ premium long detail" },
  "global_visual": {
    "palette": ["..."],
    "accent": "#5fb7c4",
    "typography": "modern geometric sans-serif headline placeholders only",
    "background_texture": "soft category cue with stable studio lighting",
    "ornaments": "thin-line icons / rounded cards / branded color band",
    "transition_overlap_px": 96
  },
  "style_lock_ref": "style-lock.json",
  "buyer_reason_card_ref": "buyer-reason-card.json",
  "sections": [
    {
      "id": "hero",
      "module": 1,
      "goal": "Hero 首屏",
      "frame_objective": "Hero advertising banner ...",
      "prompt_focus": "large product visual ...",
      "story_role": "problem-solution opener",
      "shopper_tension": "用户痛点或购买前担心",
      "visual_moment": "本段必须呈现的动作 / 机制 / 场景瞬间",
      "must_show": ["必须出现的产品结构、动作或证据"],
      "bg_color_top": "#0b2a4a",
      "bg_color_bottom": "#1e6f9a",
      "transition_in": "首屏直接奠定视觉基调",
      "transition_out": "底部 15% 预留可延展背景",
      "shared_elements": ["品牌色带", "细线装饰"],
      "claims_allowed": ["..."],
      "claims_for_review": ["..."],
      "image_copy_gate": {
        "headline_en": "Daily Support, Naturally Pure",
        "headline_localized": null,
        "support_labels": ["Clean ingredients", "Daily wellness", "Trusted source"],
        "proof_line": "Backed by 3rd-party testing (placeholder until provided)",
        "cta": "soft CTA"
      },
      "category_hint": {
        "palette": ["..."],
        "scenes": ["..."],
        "ornaments": ["..."],
        "headline_directions": ["..."]
      },
      "assumptions_used": [
        { "field": "category", "label": "Inferred", "reason": "based on product name" }
      ]
    }
  ],
  "assumptions_used": [
    { "field": "compliance_preference", "label": "Default", "reason": "user did not opt-in" }
  ]
}
```

兼容性：

- 旧 `detail-plan.json`（缺 `profile` / `category` / `image_copy_gate` 等字段）按 `legacy-long-7` 解析；缺失 `image_copy_gate` 时脚本会按段位 fallback 写入空对象，避免 prompt 失败。
- 相邻 section 的 `bg_color_bottom` 与 `bg_color_top` 应一致或在同一色相渐变范围内。

## 商品类型叙事模板

`category` 只决定视觉系统，例如色板、光线、场景和装饰；`product_type_template` 决定卖点叙事骨架。系统 MUST 在生成默认 `detail-plan.json` 时根据商品名称、品类、卖点、规格和使用场景自动匹配商品类型模板。未命中时继续使用通用 profile 模板。

首个内置模板为 `pet-travel-hydration`，用于便携宠物饮水瓶。该模板 MUST 将 8 段结构收敛到户外补水主线：户外口渴冲突、一键出水、未饮用水回流、防漏携带、550mL 出行容量、犬猫适配、材质尺寸确认、出行套装收尾。每段 MUST 有独立 `story_role / shopper_tension / visual_moment / must_show`，不得重复同一种宠物生活方式场景。

## 串行递归生成规则

默认禁止并行。

1. 上传原始商品图到公网临时 URL，作为图生图首参。
2. 生成 `00-white-background.png`，再上传到公网。
3. 启用 `--with-angle-sheet` 时生成 `angle-sheet/angle-sheet.png`，上传公网，记入 `manifest.public_references`。
4. 第 1 段以白底图（+ Angle Sheet）公网 URL + 商品信息 + 全局视觉系统生成。
5. 每生成一段 step 图片立即上传公网，作为下一段辅助参考。
6. 第 N 段（N≥2）保留上一段底部 20–30% 裁切区域；公网型 provider 必须上传该裁切图，并把裁切图 URL 作为下一段第一参考图。
7. 每段底部 15% 区域必须预留可延展背景、纹理或装饰元素。
8. 每段 prompt 必须变化，不只是替换 section 名。

## Prompt 五段式

每段 prompt 顺序：

1. **Style Lock 段**：直接复用 `style_lock.summary`。
2. **Buyer Reason 段**：写 `Primary Selling Reason: ...` + `Belief Shift: from ... to ...`。
3. **Image Copy Gate 段**：写 `Headline: "..."` + `Support labels: "..."` + `Proof line: "..."` + `CTA: "..."`，乱码风险高时附 `clean layout with short readable headline placeholders, concise labels only.`。
4. **Section Frame 段**：`Frame objective: ...` + `Section focus: ...` + `Story role: ...` + `Shopper tension: ...` + `Visual moment: ...` + `Must show: ...` + `Category cues: palette ..., scene ..., props ...`。
5. **Transition & Constraints 段**：上一段过渡描述、底部 15% 预留、禁止清单（hard cut、虚构事实、修改 Logo / 包装、贬低具体竞品、虚假认证）。启用 Angle Sheet 时追加 `Use the product angle sheet only as product identity reference.`。

## 拼接和验收

- 默认使用 provider 返回的原始 step 图作为合成输入。
- `final-detail-long.png` 由原始 step 图等比缩放到 750px 宽后直接上下拼接生成，不做中心裁剪或 alpha overlap 融合。
- 同时输出 `final-detail-long-raw-original-stacked.jpg`，将原始 step 图统一到最大原始宽度后直拼，供高清复核。
- 检查最终宽度、总高度、文件体积。
- 检查相邻接缝区域色彩跳变并写入 `warnings`。
- 输出 `final-detail-long.png` 与 `manifest.json`。

## Schema：`manifest.json`

```json
{
  "status": "success",
  "final_file": "final-detail-long.png",
  "width": 750,
  "height": 6720,
  "source": "raw",
  "resolved_source": "raw",
  "compose_mode": "stack",
  "overlap": 0,
  "seam_check_px": 40,
  "raw_original_stacked_file": "final-detail-long-raw-original-stacked.jpg",
  "raw_original_stacked_width": 1376,
  "profile": "a-plus-standard-12",
  "category": "wellness",
  "conversion_driver": "pain",
  "english_baseline": true,
  "buyer_reason_card": { "...": "Buyer Reason Card content or path" },
  "style_lock": { "...": "Style Lock content" },
  "style_lock_hash": "sha1...",
  "scorecard": {
    "conversion_clarity": "pass",
    "buyer_reason_fit": "pass",
    "english_baseline_quality": "pass",
    "mobile_readability": "pass",
    "visual_consistency": "pass",
    "platform_fit": "pass",
    "evidence_honesty": "pass"
  },
  "assumptions_used": [
    { "field": "category", "label": "Inferred", "reason": "based on product name" }
  ],
  "steps": [
    { "section": "hero", "file": "steps/step-01-hero.png", "prompt_file": "prompts/step-01-hero.txt" }
  ],
  "warnings": [],
  "review_required": [],
  "public_references": [
    { "stage": "input-product", "file": "product.png", "url": "https://tmpfiles.org/dl/..." }
  ],
  "angle_sheet": {
    "file": "angle-sheet/angle-sheet.png",
    "url": "https://tmpfiles.org/dl/..."
  }
}
```

## 视觉原则

- 一屏只讲一个核心信息。
- 产品和包装必须清晰，不能严重变形。
- 背景、纹理、曲线、装饰线稿和色板要连续。
- 图中文字要少而大，移动端可读。
- 场景服务产品，不抢主体。
- 不把几张无关海报硬拼成长图。

## 合规禁区

- 价格、优惠、限时、Coupon。
- 保修、保证、发货、退换货承诺（除非用户提供）。
- 站外链接、二维码、社媒引导。
- 无证据认证、奖项、测试数据、功效数字、营养数值、兼容声明。
- 过度绝对化表达：`best`、`No.1`、`guaranteed`。
- 无证据竞品贬低；对比图只用 generic comparison。
- 英文 on-image 文案 ≤ 8 词，参数全部转利益。
- Review 模块按 Review Compliance Switch 处理；synthetic copy 必须出现在 `assumptions_used`。

## 兼容 Amazon A+ 单模块

`profile = single-modules` 时按 `single-modules` 模板加载子模块尺寸（Basic `970x300` / Premium `1464x600` / Brand Story `1500x500`），仍走事实复核与合规边界。
