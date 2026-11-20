---
name: amazon-a-plus-graph
description: 按品类自适应生成 Amazon A+ 标准 12 模块长图。根据商品图片和商品信息，先做信息权重门 / Buyer Reason / 转化驱动诊断 / English Baseline / Campaign Style Lock，再生成白底图、可选 Product Angle Sheet、detail-plan，并按串行递归图生图产出一张 750px 宽 Amazon A+ 长图；用户明确要求时兼容简化 8 段、原通用 7 段以及单模块 A+/Premium A+/Brand Story 工作稿。用于用户提到 Amazon A+、EBC、Listing 详情页、Brand Story、Premium A+、商品图文长图、跨境电商详情图、品类化电商长图时触发。
---

# Amazon A+ Graph

## Overview

默认产物是一张按 Amazon A+ 标准结构打造的电商长图，宽度 `750px`，按 `profile` 决定段数与高度：

- 默认 profile：`a-plus-standard-12`，12 模块叙事，覆盖首屏 / 卖点 / 单品 / 拆解 / 步骤 / 场景 / 性能可视化 / 对比 / 规格 / 包装 / 信任 / 收尾。
- 简化 profile：`a-plus-lite-8`，8 段日常省钱版。
- 兼容 profile：`legacy-long-7`，旧通用 7 段长图，向后兼容旧调用与旧 `detail-plan.json`。
- 单模块兼容路径：`single-modules`，输出 Basic A+ `970x300`、Premium A+ `1464x600`、Brand Story `1500x500` 工作稿。

每次任务同步交付：

```
buyer-reason-card.json
style-lock.json
detail-plan.json
research.json
prompts/step-NN-<section>.txt
steps/step-NN-<section>.png
00-white-background.png
angle-sheet/angle-sheet.png   # 仅启用 Product Angle Sheet 时
final-detail-long.png
manifest.json
```

`manifest.json` 含 `profile`、`category`、`conversion_driver`、`buyer_reason_card`、`style_lock`、`scorecard`、`assumptions_used`、`public_references`、`review_required`、`warnings` 字段。

读取 `references/a-plus-content-spec.md` 后再开始规划结构、Prompt、拼接、事实复核与验收。品类视觉系统见 `references/amazon-aplus-style-system.md`，机器可读模板见 `references/category-profiles.json`、`references/profile-templates.json` 与 `references/product-type-templates.json`。

## Model Selection Gate

开始生成前必须先让用户选择生图模型；如果用户已经明确指定，则复述确认后继续。只提供以下三种用户可见选项：

| 选项 | CLI 参数 | 默认模型 | 适用场景 |
| --- | --- | --- | --- |
| `image2low` | `--provider image2low` | `og-image2-low` | 默认选项，沿用当前 OpenAI-compatible 串行图生图链路。 |
| `qw` | `--provider qw` | `qwen-image-2.0-pro` | 走 Qwen/DashScope 图生图链路，适合需要 Qwen 稳定风格时使用。 |
| `nanobanana` | `--provider nanobanana` | `gemini-3.1-flash-image-preview` | 走 CLPAI Gemini / Nano Banana 图生图链路，适合尝试 Gemini 图片效果。 |

模型未选定前，不得开始联网生图或批量生成。若用户没有偏好，推荐 `image2low`，但仍要先询问确认。

## Trigger Signals

中英文触发词：

- Amazon A+ / Amazon EBC / A+ Content / EBC content
- Premium A+ / A+ Premium / Brand Story / 品牌故事
- Amazon Listing 详情页 / Listing 详情图 / Listing 长图 / Listing 图文
- 商品图文详情 / 商品详情长图 / 详情页长图 / PDP 长图
- 跨境电商详情图 / 跨境电商长图 / Amazon 长图 / Seller Central 详情
- 品类化电商长图 / 数码长图 / 食品长图 / 保健长图 / 宠物长图 / 家居长图 / 美妆长图 / 户外长图 / 母婴长图 / 服饰长图 / 工具长图

通用电商长图触发时按默认 profile 走，但产物结构仍是 A+ 12 模块叙事。

## Profiles

| profile | 段数 | 适用场景 | 默认段高（px） |
| --- | --- | --- | --- |
| `a-plus-standard-12` | 12 | 高客单、品牌完整叙事、A+ Premium 候选 | 560 |
| `a-plus-lite-8` | 8 | 日常出图、预算控制、快速迭代 | 620 |
| `legacy-long-7` | 7 | 旧通用电商长图兼容、向后调用 | 620 |
| `single-modules` | 1×N | Amazon Basic / Premium A+ / Brand Story 单模块工作稿 | 按平台规范 |

切换方式：CLI 加 `--profile`，或 `detail-plan.json` 顶层加 `"profile": "..."`。`detail-plan.json` 缺省 `profile` 字段时按 `legacy-long-7` 解析，保证旧文件可跑。

## Category System

预置 10 大品类，每个品类自带色板、场景、视觉表现、英文标题方向、必做模块顺序与可选模块：

| code | 中文 | 关键词 | 推荐色系 |
| --- | --- | --- | --- |
| `tech` | 数码 / 电子 | minimal tech / precise / clean workspace | 银白、深灰、黑、科技蓝、冷光紫、荧光绿点缀 |
| `food` | 食品 / 饮料 | fresh / natural / clean food branding | 奶白、浅金、浅绿、天空蓝、暖橙、原木 |
| `wellness` | 保健 / 营养 | scientific / premium health / trustworthy | 深蓝、海洋蓝、白、金、浅青、医疗绿 |
| `pet` | 宠物 | warm home / pet friendly / soft premium | 米白、浅棕、暖灰、原木、奶油、低饱和绿 |
| `home` | 家居 / 生活 | modern home / clean living / functional beauty | 米白、浅灰、原木、奶油、香槟金、低饱和蓝绿 |
| `beauty` | 美妆 / 个护 | elegant / soft beauty / clean skincare | 奶白、浅粉、香槟金、浅紫、水蓝、珍珠 |
| `outdoor` | 户外 / 运动 | durable / active / outdoor premium | 深绿、沙色、黑、橙、军绿、深蓝 |
| `baby` | 母婴 / 儿童 | safe / gentle / family trust | 奶白、浅黄、浅蓝、浅粉、薄荷绿、原木 |
| `apparel` | 服饰 / 配饰 | lifestyle fashion / clean premium / everyday wear | 黑白灰、米色、棕、香槟金、深蓝 |
| `tools` | 工具 / 五金 / 汽车 | reliable / strong / heavy-duty | 黑、深灰、金属银、工业蓝、橙、红色点缀 |

`category` 通过 CLI `--category` 指定；缺省 `auto` 时由 agent 根据商品名 + `research.json` 推断，结果写入 `assumptions_used` 并以 `Inferred` 标记。每个品类的完整字段见 `references/category-profiles.json`，叙事策略见 `references/amazon-aplus-style-system.md`。

## Minimum Input Resolution Gate

收集最小输入时按以下权重处理，高权重覆盖低权重：

1. **User-provided**：用户文本、上传图片、参考图、链接、文件名。
2. **Attachment/context**：附件、历史上下文、项目文件。
3. **Web-researched**：联网研究产品官网、品牌页、平台规则、可查测评（首选 agent 内置 web 工具，无内置工具时调用 `scripts/research_web.py`）。
4. **Inferred**：基于品类、渠道、市场做合理推断。
5. **Assumption**：明确假设，写入 `assumptions_used`。
6. **Default**：Skill 默认值（profile 默认 `a-plus-standard-12`、宽度 750、英文 baseline、默认 Style Lock）。

每条事实在 `research.json` 与 `detail-plan.json` 中均带 `source_label` 字段。最终输出必须给出 **Assumptions / Defaults Used** 段，列出 `Inferred` / `Assumption` / `Default`。

**Compliance Preference** 默认 `ignored`；用户明确说「考虑合规 / 平台合规 / 广告合规 / 类目合规 / 风险审查」才进入 Compliance Path（询问目标平台 / 国家 / 类目 / 禁用表达，输出可用、需证据、建议弱化三类表达）。

**Review Compliance Switch**：

- `enabled`：仅使用真实好评 / 真实推荐 / 真实评论主题。无真实素材时跳过 Trust 模块，用 Benefit / How-to-Use / FAQ / 保障 / 场景图替代。
- `disabled`（默认）：允许编写模拟好评 / review-style quote，但必须在 `assumptions_used` 中显式声明为 `Default: synthetic review copy`。第三方平台截图、真实用户名、可核验评价数量仅在用户提供真实素材时使用。

## Buyer Reason Card

任何任务先输出 `buyer-reason-card.json`（8 字段）：

```json
{
  "target_buyer": "谁在买，使用场景",
  "purchase_trigger": "为什么现在会考虑买",
  "belief_shift": "图片要让用户从旧认知转到新认知",
  "primary_selling_reason": "唯一主购买理由",
  "proof_material": "已有证据或 proof placeholder",
  "review_recommendation_material": "真实评价 / 推荐 / 主题；按 Switch 决定",
  "offer_lever": "价格 / 组合 / 保障 / 物流 / 赠品 / 低风险承诺",
  "evidence_bound_claims": ["数据 / 认证 / 销量 / 真实评价 / 品牌授权，仅在有证据时使用"]
}
```

Buyer Reason Card 决定后续每段 `frame_objective` 与图内文案。

## Conversion Driver Diagnosis

三选一：

- `visual`：成交靠看见。适合外观、质感、礼品感、Before/After。Hero 用 thumb-stop visual claim，中段重质感与场景。
- `pain`：成交靠问题紧迫。强制顺序：Pain mining → Solution mechanism → Trust → Offer + CTA。
- `emotion`：成交靠身份、向往、情绪价值。Hero 用 emotional scene hook + identity statement。

主驱动力写入 `manifest.json` 顶层 `conversion_driver`，并约束每段 prompt 的 frame_objective。

## English Baseline + Localization Layer

跨境默认先输出英文（美国市场）baseline：

1. Conversion diagnosis summary
2. Buyer Reason Card
3. Section-level frame objective + on-image headline + support labels
4. Offer + CTA architecture
5. Assumptions / Defaults Used + Test Priorities

英文 on-image 文案规则：

- 大标题 ≤ 8 词。
- 卖点解释 ≤ 12 词。
- 参数转利益（DPI → smoother control，protein g → daily energy 等）。

如用户要求本地化，再叠加 Localization Layer：保留转化意图，按目标市场重写说服文案，适配单位、长度、文化敏感词；`detail-plan.json` 的每段 `image_copy_gate` 同时保留 `headline_en` 与 `headline_localized`。

## Campaign Style Lock

多段长图必填，输出 `style-lock.json`，10 字段：

1. `visual_direction`（如 premium tech ecommerce / clean household care / warm gift editorial）
2. `palette`（2–3 主色 + 1 accent + 黑白灰）
3. `temperature`（warm / cool / neutral）
4. `font_system`（一套现代无衬线，如 modern geometric sans-serif headline placeholders）
5. `background_system`（studio / tabletop / lifestyle room / outdoor 等）
6. `lighting_system`（方向、阴影、反射、情绪）
7. `layout_system`（留白、圆角卡片、信息标签、标号、图表组件）
8. `icon_system`（线性 / 轻 3D 二选一，描边宽度、复杂度）
9. `product_presentation`（角度、比例、位置、材质表现）
10. `consistency_requirements`（固定色板、单一字体、稳定背景、统一光线、匹配图标）

每段 Prompt 第一段必须复用同一段 `style_lock.summary`（一段文本）。`manifest.json` 记录 `style_lock_hash`，便于发现某段被污染。

## Image Copy Gate

每段 Prompt 写出前必须先确定图内文案：

- `frame_objective`：这一段推动什么转化动作。
- `headline`：3–7 词英文短句。
- `support_labels`：2–4 个短标签。
- `proof_line`：仅当有证据 / placeholder 时出现。
- `review_line`：按 Review Compliance Switch 决定。
- `cta_style`：direct / soft / risk reversal / bundle / omitted。

模型容易生成乱码时，prompt 内统一写：`clean layout with short readable headline placeholders, concise labels only`。

## Product Angle Sheet（可选）

实物商品建议启用 `--with-angle-sheet`，在白底图之后、首段之前生成一张临时多角度参考表，仅用于「锁产品身份」：

必含角度（按品类裁剪）：正面、左 45°、右 45°、侧面厚度、背面 / 磁吸面、接口 / 按键 / LED 关键结构、产品 + 包装组合、关键使用角度。

正式段 Prompt 中只允许出现这一句：

```
Use the product angle sheet only as product identity reference.
```

不再描述 angle sheet 本身的版式细节。Angle Sheet 公网 URL 与本地路径写入 `manifest.public_references` 与 `manifest.angle_sheet`。

## Default Workflow

1. 收集输入 + Minimum Input Resolution Gate（含 Compliance Preference / Review Switch）。
2. 进入 Model Selection Gate，让用户在 `image2low` / `qw` / `nanobanana` 中选择。
3. 输出 `buyer-reason-card.json` + Conversion Driver。
4. 写 English Baseline，必要时叠 Localization Layer。
5. 选 `profile`（默认 `a-plus-standard-12`）+ `category`（默认 `auto`），加载 `references/profile-templates.json`、`references/category-profiles.json` 与商品类型叙事模板。
6. 写 `style-lock.json`（按 category 默认值起手，按 driver 调整）。
7. 联网研究 → `research.json`：内置 web 工具优先；否则用 `scripts/research_web.py`。
8. 按用户选择的模型链路生成 `00-white-background.png`；`image2low` 链路上传原始商品图和白底图作为公网参考，`qw` / `nanobanana` 链路直接使用本地参考图。
9. 启用 `--with-angle-sheet` 时生成 Angle Sheet；仅 `image2low` 链路上传公网。
10. 写 `detail-plan.json`，按 `profile + product_type_template` 填充 N 段；商品类型模板负责叙事骨架，category 只负责视觉系统。每段含 `id / goal / frame_objective / prompt_focus / story_role / shopper_tension / visual_moment / must_show / image_copy_gate / category_hint / assumptions_used`。
11. Image Copy Gate：把每段 `image_copy_gate.headline / labels / proof / cta` 全部确定，再进入生图。
12. 串行递归生成：第 N 段参考上一段、本段白底图和原始商品图；prompt 必含 Style Lock + Buyer Reason 关键句 + Image Copy Gate + Frame Objective + 上一段过渡 + 底部 15% 预留 + 禁止清单。
13. 拼接：默认使用 provider 返回的原始分段图，等比缩放到 750px 宽后直接上下拼接，输出 `final-detail-long.png`；同时保留一份统一到最大原始宽度的 `final-detail-long-raw-original-stacked.jpg` 供高清复核。
14. Self-review Scorecard 7 项 Pass/Fail 写入 `manifest.scorecard`。
15. 中文交付报告。

默认禁止并行；任何段失败不允许跳段，必须修后续上链。

## Prompt Rules

每段 Prompt 五段式：

1. **Style Lock 段**：复用 `style_lock.summary`，禁止改动。
2. **Buyer Reason 段**：写 `Primary Selling Reason: ...` + `Belief Shift: from ... to ...`。
3. **Image Copy Gate 段**：写 `Headline: "..."` + `Support labels: "..."` + `Proof line: "..."` + `CTA: "..."`；模型乱码时加上 `clean layout with short readable headline placeholders, concise labels only.`。
4. **Section Frame 段**：写 `Frame objective: ...` + 该段 `prompt_focus` + Category 视觉建议（色板 / 场景 / 道具）。
5. **Transition & Constraints 段**：上一段过渡描述、底部 15% 预留、禁止清单（hard cut、虚构事实、修改 Logo / 包装、贬低具体竞品、虚假认证）。

启用 Angle Sheet 时统一在第 5 段末尾追加：`Use the product angle sheet only as product identity reference.`

Hero 段（首段）固定模板：

```text
[Style Lock]
Primary Selling Reason: ...
Belief Shift: from ... to ...
Headline: "..."
Support labels: "..."
Proof line: "..." | omitted
CTA: "..." | omitted
Frame objective: hero advertising banner that establishes brand and primary selling reason within 1 second.
Section focus: ...
Category cues: palette ..., scene ..., props ....
Reference image 1: white-background product (URL).
Reference image 2: original product photo for package detail.
Bottom transition: reserve the bottom 15% as extendable background/texture/ornament for the next section.
Avoid: hard cut lines, invented claims, fake certifications, package/logo changes.
Use the product angle sheet only as product identity reference.   # 仅启用 angle-sheet 时保留
```

中段（N≥2）固定模板：

```text
[Style Lock]
Primary Selling Reason: ...
Belief Shift: from ... to ...
Headline: "..."
Support labels: "..."
Proof line: "..." | omitted
CTA: "..." | omitted
Frame objective: section [N] / [section_id] — ...
Section focus: ...
Category cues: ...
Reference image 1: previous section bottom crop (URL, first reference for public-URL providers). Top 20% of this section must continue its color, texture, and ornaments.
Reference image 2: white-background product (URL).
Reference image 3: original product photo.
Transition in: ...
Transition out: bottom 15% reserved for the next section.
Avoid: hard cut lines, sudden background jumps, repeated previous-section content, invented claims, package/logo changes.
Use the product angle sheet only as product identity reference.   # 仅启用 angle-sheet 时保留
```

Closing 段（最后一段）追加：`Final emotional headline only; do not pile new selling points.`

## Compliance Checklist

交付前检查：

- 不出现价格、折扣、Coupon、限时、促销秒杀。
- 不出现保修、保证、发货、退换货承诺，除非用户提供。
- 不出现外链、二维码、社媒引导。
- 不出现无证据认证、奖项、销量、销榜、原产地、功效数字、营养数值、兼容声明。
- 不出现 `best`、`No.1`、`guaranteed` 等绝对化表达。
- 不贬低具体竞品品牌；对比图只用 generic comparison。
- 英文 on-image 文案 ≤ 8 词，参数全部转利益。
- 真实 Logo 与包装结构不变形。
- 段间过渡视觉连续，无硬切边、无突兀色块。
- Review 模块按 Review Compliance Switch 处理；synthetic copy 必须出现在 `assumptions_used`。
- `manifest.scorecard` 7 项至少 6 项 Pass，否则改 prompt 重生关键段。

## Self-review Scorecard

写入 `manifest.scorecard`：

| key | 检查项 |
| --- | --- |
| `conversion_clarity` | 首屏 1 秒内能看出主购买理由 |
| `buyer_reason_fit` | 每段都服务 Buyer Reason Card 的主理由 |
| `english_baseline_quality` | 英文文案像自然跨境商品文案，不像翻译腔 |
| `mobile_readability` | 图内文字短、清楚、层级强、移动端可读 |
| `visual_consistency` | 全段复用同一 Style Lock，色板 / 字体 / 光线一致 |
| `platform_fit` | 适配 Amazon A+ / EBC 语境，不像淘宝详情页 |
| `evidence_honesty` | 无虚构数据 / 认证 / 评分；synthetic review 已声明 |

每项值 `pass` / `fail` / `na`，`fail` 必须附 `reason`。

## Output Contract

中文交付块（默认）：

```text
已生成 Amazon A+ 长图：
- profile: a-plus-standard-12 / a-plus-lite-8 / legacy-long-7 / single-modules
- category: tech / food / wellness / ...
- conversion_driver: visual / pain / emotion
- generation_provider: image2low / qw / nanobanana
- generation_model: og-image2-low / qwen-image-2.0-pro / gemini-3.1-flash-image-preview
- final-detail-long: /absolute/path/final-detail-long.png
- white-background: /absolute/path/00-white-background.png
- angle-sheet: /absolute/path/angle-sheet/angle-sheet.png   # 启用时
- buyer-reason-card: /absolute/path/buyer-reason-card.json
- style-lock: /absolute/path/style-lock.json
- detail-plan: /absolute/path/detail-plan.json
- research: /absolute/path/research.json
- manifest: /absolute/path/manifest.json

事实来源摘要：...
Assumptions / Defaults Used：...
Self-review Scorecard：7/7 pass / X fail（附原因）
合规检查：通过 / 需人工复核
拼接 / 尺寸警告：...
```

## Compatibility

- `--profile legacy-long-7`：复现旧 7 段通用电商长图行为；旧 `detail-plan.json`（无 `profile` 字段）自动按此 profile 解析。
- `--profile a-plus-lite-8`：8 段简化版，节省 API 成本，适合日常迭代。
- `--profile single-modules`：兼容 Basic A+（`970x300`）、Premium A+（`1464x600`）、Brand Story（`1500x500`）单模块工作稿，仍走 fact-boundary 与 compliance 校验。
- `--provider image2low`：默认兼容路径，等价于原 `og-image2` 链路，默认模型 `og-image2-low`。
- `--provider qw`：等价于原 `dashscope` / Qwen 链路，默认模型 `qwen-image-2.0-pro`。
- `--provider nanobanana`：使用 `scripts/image-gemini-nanobanana/generate.py`，默认模型 `gemini-3.1-flash-image-preview`。
- 所有兼容路径都必须输出 `style-lock.json` 与 `manifest.scorecard`，方便长短图统一审稿。
