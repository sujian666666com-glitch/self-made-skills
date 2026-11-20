# 自研 Skills

个人自研的 Claude Code / Agent Skills 合集，每个目录是一个独立 skill（含 `SKILL.md` 及配套脚本、参考资料）。

## 技能列表

| Skill | 说明 |
| --- | --- |
| [amazon-a-plus-graph](./amazon-a-plus-graph) | 按品类自适应生成 Amazon A+ 标准 12 模块长图（750px 宽）：先做信息权重诊断、Buyer Reason、English Baseline、Campaign Style Lock，再生成白底图、detail-plan，并串行图生图产出长图；兼容简化 8 段、旧 7 段与单模块 / Premium A+ / Brand Story 工作稿。 |
| [amazon-product-pic-generator](./amazon-product-pic-generator) | 从产品原图生成 2000×2000 Amazon Listing 图片包（主图白底、卖点信息图、生活方式、使用中、细节、尺寸、对比、包装等图位），通过 og-image2 API 批量生成并输出 manifest。 |
| [rfc-design-doc](./rfc-design-doc) | 生成 RFC 风格设计文档并按编号落盘（默认 `docs/design/NNNN-标题.md`），固定包含需求理解、接口改动、数据库改动、mermaid 流程图、范围边界、验收标准、影响面、回滚方案八节。 |
| [x-gen](./x-gen) | 通过 XXZ API 生成图片和视频，覆盖文生图、图生图、文生视频、图生视频，支持 gpt-image-2、nano-banana-2、nano-banana-pro、grok-video-3 等模型。 |

## 使用方式

将需要的 skill 目录复制或软链到对应 Agent 的 skills 目录，例如 Claude Code：

```bash
ln -s "$(pwd)/amazon-a-plus-graph" ~/.claude/skills/amazon-a-plus-graph
ln -s "$(pwd)/amazon-product-pic-generator" ~/.claude/skills/amazon-product-pic-generator
ln -s "$(pwd)/rfc-design-doc" ~/.claude/skills/rfc-design-doc
ln -s "$(pwd)/x-gen" ~/.claude/skills/x-gen
```

## 配置

涉及第三方生图 / 生视频接口的 skill 通过环境变量读取密钥，不随仓库提交：

- `amazon-a-plus-graph`：`DASHSCOPE_API_KEY`（可选 `TAVILY_API_KEY` 用于联网调研）
- `amazon-product-pic-generator`：`OG_IMAGE2_API_KEY`、`OG_IMAGE2_API_URL`、`OG_IMAGE2_MODEL`，参考 `script/.env.example`
- `x-gen`：`XXZ_API_KEY`，参考 `scripts/README.md`

## 目录结构

```
.
├── amazon-a-plus-graph/          # A+ 长图生成
│   ├── SKILL.md
│   ├── agents/
│   ├── references/
│   └── scripts/
├── amazon-product-pic-generator/ # Listing 产品套图
│   ├── SKILL.md
│   ├── docs.md
│   ├── references/
│   └── script/
├── rfc-design-doc/               # RFC 设计文档
│   └── SKILL.md
└── x-gen/                        # 图片 / 视频生成
    ├── SKILL.md
    ├── api-reference.md
    ├── HOW-TO-GENERATE.md
    └── scripts/
```
