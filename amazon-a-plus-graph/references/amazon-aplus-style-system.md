# Amazon A+ 风格建议体系（skill 内嵌精简版）

> 本文档面向 `amazon-a-plus-graph` skill 的运行时使用，是 `Amazon A+ 风格建议体系.md` 的精简、可执行版本。
> 总原则：不固定模板，固定长图组成逻辑；不同品类换色板、场景、道具与情绪，但叙事节奏统一为「首屏吸引 → 中段解释 → 场景代入 → 证据支撑 → 参数确认 → 品牌收尾」。

---

## Part A：12 模块标准长图模板

每个模块给出：目的、画面内容、文案结构、设计要求。`profile = a-plus-standard-12` 默认全选；`a-plus-lite-8` 取模块 1/2/4/5/6/8/9/12；`legacy-long-7` 复用旧 7 段映射（见末尾对照表）。

### 模块 1 — Hero 首屏主视觉

- **目的**：1 秒内建立高级感、品类识别、核心利益。
- **画面**：产品大图占 40–60%，品牌 Logo，产品名，一句核心利益标题，品类相关高级背景，1–2 个视觉符号。
- **文案**：`[Product Name]` + `[Core Benefit Title ≤ 8 words]` + 一句日常使用价值副标题。
- **要求**：标题大、清晰；产品真实质感；不堆参数；背景服务产品不抢主体。

### 模块 2 — 核心卖点 Icon 卡片

- **目的**：快速告诉用户为什么值得买。
- **画面**：3–5 个圆角卡片，每卡 = icon + 短标题 + 一句解释，可附小产品局部图。
- **文案**：`Icon` / `Benefit Title (≤ 4 words)` / `One-line explanation (≤ 12 words)`。
- **要求**：图标风格统一；卡片圆角统一；卖点从「参数」转「用户利益」。

### 模块 3 — 产品单体高级展示

- **目的**：让用户看清产品本身，提高信任感。
- **画面**：产品单体大图 + 包装盒 / 配件 / 原料可选 + 干净背景 + 少量卖点标注；产品居中或偏左，右侧 2–3 个短标签，下方一句品牌 slogan。
- **要求**：边缘清晰；阴影自然；包装文字不变形。

### 模块 4 — 功能 / 成分 / 结构拆解

- **目的**：解释产品为什么好。
- **画面**：产品局部放大 + 箭头标注 + 半透明信息卡 + 简短英文说明；最多 5 个标注点；标注线细、不乱。
- **要求**：不要做成说明书；同段内可叠 1 张爆炸图或剖面图。

### 模块 5 — 使用步骤

- **目的**：降低理解成本。
- **画面**：3 或 4 步，每步真实小图，图文比 7:3，序号 `01 / 02 / 03 / 04`。
- **要求**：步骤短、可扫读；不要超过 4 步。

### 模块 6 — 真实生活方式场景

- **目的**：让用户产生代入感。
- **画面**：人物 / 宠物 / 家庭 / 办公 / 户外场景，产品在真实使用，配一句情绪型标题。
- **要求**：场景真实、不像合成；产品可见；人物表情自然；背景干净。

### 模块 7 — 性能 / 功效可视化

- **目的**：把抽象优势做成视觉证据。
- **画面**：柱状图 / 曲线图 / 对比条 / 进度卡片 / Before-After / 功能 icon 环绕。
- **要求**：数据真实或写 `conceptual visual`；图表简洁；不要像 Excel 截图。

### 模块 8 — Why Choose Us 对比

- **目的**：建立购买理由。
- **画面**：本品 vs 普通产品（generic comparison only），或 4 条 reasons to choose us。
- **要求**：不贬低具体竞品；对比表 ≤ 5 行；视觉突出本品优势。

### 模块 9 — 规格 / 参数 / 成分 / 营养表

- **目的**：给理性用户最后确认。
- **画面**：左侧产品或包装图 + 右侧表格 + 底部一行说明；按品类换 Tech Specs / Nutrition Facts / Supplement Facts / Size Guide / Material Info / Package Includes。
- **要求**：放中后段，不放首屏；表格干净、字号可读。

### 模块 10 — 包装 / 配件 / 套装展示

- **目的**：让用户知道买到什么。
- **画面**：整齐陈列，透视统一，包装文字清晰；按品类换内含物列表。
- **要求**：不堆放；不用乱角度。

### 模块 11 — 用户评价 / 信任背书

- **目的**：提升购买信任。
- **画面**：评价卡片 / 星级 / 用户头像 / 使用场景照片 / 品牌承诺 / 检测或认证图标。
- **要求**：按 Review Compliance Switch 处理；不伪造平台评价、不伪造认证标识。`enabled` 时无真实素材直接跳过该模块，用利益、步骤、FAQ 或场景图替换。

### 模块 12 — Closing 情绪收尾

- **目的**：强化品牌记忆，推动转化。
- **画面**：产品最终大图 + 品牌 Logo + 一句强收尾标题 + 生活方式背景 + 简洁 CTA。
- **要求**：只保留一个核心情绪；不再堆卖点；像广告结尾。

### Profile 段位映射

| profile | 段 1 | 段 2 | 段 3 | 段 4 | 段 5 | 段 6 | 段 7 | 段 8 | 段 9 | 段 10 | 段 11 | 段 12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `a-plus-standard-12` | 1 Hero | 2 Benefits | 3 Showcase | 4 Breakdown | 5 How-to | 6 Lifestyle | 7 Performance | 8 Why-Us | 9 Specs | 10 Package | 11 Trust | 12 Closing |
| `a-plus-lite-8` | 1 Hero | 2 Benefits | 4 Breakdown | 5 How-to | 6 Lifestyle | 8 Why-Us | 9 Specs | 12 Closing | — | — | — | — |
| `legacy-long-7` | 1 Hero (= hero) | 2 Benefits (= selling-points) | 11 Trust 简版 (= quality-story) | 3 Showcase (= product-focus) | 6 Lifestyle (= scenario-proof) | 9 Specs (= spec-table) | 12 Closing (= footer) | — | — | — | — | — |

`legacy-long-7` 的 section id 沿用旧名 `hero / selling-points / quality-story / product-focus / scenario-proof / spec-table / footer`，确保旧 plan 文件向后兼容。

---

## Part B：10 品类视觉指南

每个品类列：风格关键词、推荐色系、推荐场景、视觉表现、英文标题方向、最容易踩的雷。完整字段（机器可读）见 `category-profiles.json`。

### tech 数码 / 电子

- 关键词：Minimal Tech / Futuristic / Precise / Clean Workspace / Apple-like Premium。
- 色系：银白、深灰、黑、科技蓝；荧光绿 / 冷光紫作 accent。
- 场景：极简办公桌、MacBook 桌面、RGB 游戏桌面、远程办公、学习、差旅便携。
- 视觉表现：产品大特写、精准光轨、半透明信息卡、微距细节、冷色渐变背景。
- 英文标题：`Precision Meets Control` / `Built for Every Setup` / `Faster Response, Smoother Workflow` / `Designed for Work and Play`。
- 雷：避免做成国产参数堆叠页，参数转利益。

### food 食品 / 饮料

- 关键词：Fresh / Natural / Healthy / Clean Food Branding / Warm Lifestyle。
- 色系：奶白、浅金、浅绿、天空蓝、暖橙、原木。
- 场景：早餐桌、厨房、办公轻食、户外野餐、家庭分享、原产地 / 牧场。
- 视觉表现：食物真实质感、原料飞溅 / 倒入杯中、自然阳光、成分卡片、营养信息模块。
- 英文标题：`Naturally Fresh, Every Day` / `Start Your Morning Better` / `Simple Ingredients, Real Taste` / `Clean Nutrition for Daily Life`。
- 雷：不要过度科技感；重点是自然、真实、有食欲。

### wellness 保健 / 营养

- 关键词：Scientific / Premium Health / Trustworthy / Clean Wellness / Professional。
- 色系：深蓝、海洋蓝、白、金、浅青、医疗绿。
- 场景：健康生活、海洋 / 自然原料、健身 / 户外、晨间补充、科学实验室轻元素。
- 视觉表现：胶囊微距、原料来源图、科学图标、成分结构图、用户状态提升图。
- 英文标题：`Daily Support for Better Wellness` / `Backed by Science, Made for Life` / `Clean Nutrition You Can Trust` / `Strength & Energy with Every Serving`。
- 雷：避免医疗化夸大；表达为 `support` / `helps` / `daily wellness`；不写治疗疾病。

### pet 宠物用品

- 关键词：Warm Home / Trustworthy / Pet Friendly / Soft Premium / Modern Living。
- 色系：米白、浅棕、暖灰、原木、奶油、低饱和绿。
- 场景：现代家居客厅、宠物进食、主人外出安心、猫狗互动、小户型自动化照护。
- 视觉表现：宠物真实互动、家居空间感、温暖自然光、功能分解图、易清洁对比。
- 英文标题：`Designed for Modern Pet Care` / `Keep Them Fed, Even When You're Away` / `Smart Care for Happy Pets` / `Cleaner, Easier, More Reliable`。
- 雷：不要太冷；重点是安心、温暖、可靠、适合家居。

### home 家居 / 生活

- 关键词：Modern Home / Clean Living / Soft Minimal / Functional Beauty / Everyday Comfort。
- 色系：米白、浅灰、原木、奶油、香槟金、低饱和蓝绿。
- 场景：客厅、厨房、浴室、卧室、收纳前后对比、家庭日常。
- 视觉表现：Before/After 对比、空间整理效果、使用步骤、材质细节、尺寸说明。
- 英文标题：`Make Everyday Living Easier` / `Simple Design, Better Home` / `Clean Space, Comfortable Life` / `Built for Daily Use`。
- 雷：避免杂乱背景；空间越干净，产品越显高级。

### beauty 美妆 / 个护

- 关键词：Elegant / Soft Beauty / Clean Skincare / Refined / Premium Self-care。
- 色系：奶白、浅粉、香槟金、浅紫、水蓝、珍珠。
- 场景：浴室洗漱台、梳妆台、肌肤微距、香氛生活、自然光窗边、礼盒。
- 视觉表现：水滴 / 泡沫 / 精华质感、肌肤触感图、成分可视化、Before/After 气色对比。
- 英文标题：`Glow Naturally Every Day` / `Clean Care for Beautiful Skin` / `A Softer Ritual for Self-care` / `Refined Beauty, Simple Routine`。
- 雷：不要廉价粉色堆砌；文字越少越高级。

### outdoor 户外 / 运动

- 关键词：Durable / Active / Outdoor Premium / Strong / Adventure Ready。
- 色系：深绿、沙色、黑、橙、军绿、深蓝。
- 场景：山地、露营、海边、健身房、跑步、户外旅行、车载露营。
- 视觉表现：产品在真实环境使用、防水 / 耐磨 / 承重细节、动态人物、参数图标简洁化。
- 英文标题：`Built for Every Adventure` / `Ready for Outdoor Life` / `Strong Gear for Active Days` / `Durable Design, Reliable Performance`。
- 雷：可以有力量感，但画面不能脏乱；保持广告感。

### baby 母婴 / 儿童

- 关键词：Safe / Gentle / Soft Premium / Family Trust / Clean Care。
- 色系：奶白、浅黄、浅蓝、浅粉、薄荷绿、原木。
- 场景：家庭育儿、宝宝使用、父母陪伴、儿童房、餐桌、外出携带。
- 视觉表现：柔和光线、安全材质说明、圆角卡片、可爱但不幼稚的图标、清洁 / 收纳展示。
- 英文标题：`Gentle Care for Little Ones` / `Safe Design for Everyday Use` / `Made for Growing Families` / `Simple, Safe, Parent-approved`。
- 雷：避免过度夸张；核心是安全、温和、可信赖。

### apparel 服饰 / 配饰

- 关键词：Lifestyle Fashion / Clean Premium / Comfortable / Stylish / Everyday Wear。
- 色系：黑白灰、米色、棕、香槟金、深蓝、低饱和彩色。
- 场景：街拍、通勤、旅行、健身、居家、礼品场景、穿搭组合。
- 视觉表现：模特真实穿戴、材质微距、尺寸说明、多角度展示、搭配场景。
- 英文标题：`Designed for Everyday Style` / `Comfort That Moves With You` / `Simple Look, Premium Feel` / `Made for Work, Travel and Life`。
- 雷：重视模特和质感，不要只做白底产品拼图。

### tools 工具 / 五金 / 汽车

- 关键词：Reliable / Strong / Practical / Professional / Heavy-duty。
- 色系：黑、深灰、金属银、工业蓝、橙、红色点缀。
- 场景：车库、维修台、汽车内饰、户外修理、工具墙、使用过程。
- 视觉表现：金属质感、强对比光影、功能拆解、尺寸 / 承重 / 耐用说明、对比普通产品。
- 英文标题：`Built to Handle the Job` / `Reliable Tools for Daily Work` / `Strong Design, Practical Use` / `Made for Tough Tasks`。
- 雷：可硬朗，但排版必须干净；不要做成低端五金详情页。

---

## Part C：品类必做模块优先级

按品类列「必做模块」与「可选模块」。`profile = a-plus-standard-12` 时全部 12 模块都生成；`a-plus-lite-8` 时优先保留必做模块。

| 品类 | 必做模块（按段位） | 可选模块 |
| --- | --- | --- |
| tech | 1 Hero / 2 Benefits / 4 Breakdown / 6 Lifestyle / 7 Performance / 9 Specs / 10 Package / 12 Closing | 5 How-to / 8 Why-Us / 11 Trust |
| food | 1 Hero / 4 Breakdown（原料）/ 2 Benefits / 6 Lifestyle / 5 How-to / 9 Specs（营养）/ 10 Package / 12 Closing | 8 Why-Us / 11 Trust / 7 Performance |
| wellness | 1 Hero / 2 Benefits（成分）/ 4 Breakdown（科学）/ 5 How-to / 6 Lifestyle / 9 Specs（Supplement Facts）/ 12 Closing | 7 Performance（周期效果）/ 11 Trust |
| pet | 1 Hero / 6 Lifestyle（宠物使用）/ 2 Benefits / 4 Breakdown / 9 Specs / 11 Trust / 12 Closing | 8 Why-Us / 5 How-to |
| home | 1 Hero / 2 Benefits / 4 Breakdown / 6 Lifestyle / 5 How-to / 8 Why-Us / 9 Specs / 12 Closing | 7 Performance / 11 Trust |
| beauty | 1 Hero / 4 Breakdown（成分）/ 5 How-to / 6 Lifestyle / 7 Performance（Before/After）/ 10 Package / 12 Closing | 11 Trust / 8 Why-Us |
| outdoor | 1 Hero / 6 Lifestyle（户外）/ 4 Breakdown（材质）/ 7 Performance / 9 Specs / 10 Package / 12 Closing | 8 Why-Us / 11 Trust |
| baby | 1 Hero / 4 Breakdown（材质安全）/ 5 How-to / 6 Lifestyle / 11 Trust / 9 Specs / 12 Closing | 2 Benefits / 8 Why-Us |
| apparel | 1 Hero / 6 Lifestyle（穿搭）/ 4 Breakdown（材质）/ 9 Specs（Size Guide）/ 10 Package / 12 Closing | 7 Performance / 11 Trust |
| tools | 1 Hero / 4 Breakdown / 7 Performance / 9 Specs / 10 Package / 8 Why-Us / 12 Closing | 6 Lifestyle / 5 How-to |

---

## Part D：通用设计规范

### 版式

- 每屏只讲一个主题。
- 大标题 + 小说明 + 主视觉。
- 卡片圆角统一。
- 模块之间用波浪、渐变、留白自然过渡。
- 不整屏铺满文字。

### 字体

- 英文为主：大标题粗体无衬线、小标题中粗、正文常规、关键词可大写。
- 中文（如必须）：只放短标题，不放大段中文，不用廉价电商字体。

### 色彩

- 每个产品最多 1 主色 + 1 辅助色 + 黑白灰。
- 色彩跟品类匹配。
- 不同产品可换色，但质感统一。

### 图标

- 线性 icon 或轻 3D icon 二选一，单图不混用。
- icon 不要过花。

### 光影

- 产品必须有自然阴影。
- 高光服务质感。
- 科技类可加光轨；食品类可加自然阳光；美妆类可加水光。

### 文案

- 英文短句。
- 标题 ≤ 8 词。
- 每个卖点解释 ≤ 12 词。
- 参数转利益。

---

## Part E：AI 起手提示词

### 基础版（适用于 lite 8 段或快速出图）

```text
Create a premium Amazon A+ Content / EBC vertical long image for [PRODUCT NAME].

Design direction:
Premium international Amazon brand style, clean modern advertising layout,
strong product focus, realistic lifestyle scenes, modular information sections,
elegant typography, high-end commercial lighting, refined icons, rounded cards,
balanced whitespace, strong visual hierarchy.

Adapt to product category: use category-appropriate colors, scenes, props, emotional tone.
Keep the system clean, premium, trustworthy, modern, Amazon-ready.
Product is always the visual hero. Benefits use short English copy.
Use lifestyle imagery for real usage. Use detail close-ups for materials, features, structure.

Avoid cheap Taobao layout, excessive text, messy decorations, low-quality icons,
random colors, over-saturated backgrounds, cluttered composition, fake-looking rendering.

Output: a complete A+ vertical long image with 8 sections:
1. Hero banner
2. Core benefits
3. Feature details
4. How to use
5. Lifestyle scenario
6. Why choose us comparison
7. Specs / ingredients / nutrition
8. Brand closing
```

### 完整版（适用于 standard 12 段）

```text
Create a premium Amazon A+ Content / EBC vertical long image for [PRODUCT NAME].

Build it as a complete modular long image with 12 sections:

1. Hero advertising banner with large product visual, brand name,
   product name, and one strong benefit headline.
2. Core benefits section with 3–5 rounded icon cards.
3. Premium single product showcase with clean background and soft shadows.
4. Feature detail breakdown with close-up product views and refined callout lines.
5. How-to-use section with 3 or 4 simple visual steps.
6. Realistic lifestyle scene showing the product in actual use.
7. Performance / benefit visualization using simple charts, icons, or comparison bars.
8. Why choose us comparison section, generic product comparison only.
9. Specs / ingredients / nutrition / material information table.
10. Package includes / accessories / multi-pack display.
11. Trust section with brand promise, review-style cards, or quality assurance icons.
12. Closing brand image with product, lifestyle background, and final emotional headline.

Visual style:
Premium international Amazon brand style, clean modern advertising layout,
strong product focus, realistic lifestyle scenes, modular information sections,
elegant typography, high-end commercial lighting, refined icons, rounded cards,
balanced whitespace, strong visual hierarchy.

Adapt the color palette, scenes, props, and emotional tone to the product category
while keeping the overall system premium, clean, trustworthy, modern, and Amazon-ready.

Avoid cheap Taobao layout, excessive text, messy decorations, low-quality icons,
random colors, over-saturated backgrounds, cluttered composition, fake-looking rendering,
and unreadable small text.
```

---

## 一句话总结

> 一张高级 A+ 长图，本质是：首屏吸引、中段解释、场景代入、证据支撑、参数确认、品牌收尾。
