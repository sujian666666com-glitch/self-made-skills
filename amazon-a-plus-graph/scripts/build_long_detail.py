#!/usr/bin/env python3
"""Build a serially generated Amazon A+ long-detail image workflow.

Default profile: a-plus-standard-12 (Amazon A+ standard 12 modules).
Compatible profiles: a-plus-lite-8, legacy-long-7, single-modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[ERROR] Missing dependency: Pillow. Install with: pip install pillow", file=sys.stderr)
    sys.exit(1)


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = SKILL_ROOT / "references"
PROFILE_TEMPLATES_PATH = REFERENCES_DIR / "profile-templates.json"
CATEGORY_PROFILES_PATH = REFERENCES_DIR / "category-profiles.json"
PRODUCT_TYPE_TEMPLATES_PATH = REFERENCES_DIR / "product-type-templates.json"

PROFILE_CHOICES = ["a-plus-standard-12", "a-plus-lite-8", "legacy-long-7", "single-modules"]
CATEGORY_CHOICES = [
    "auto", "tech", "food", "wellness", "pet", "home",
    "beauty", "outdoor", "baby", "apparel", "tools",
]
CONVERSION_DRIVER_CHOICES = ["auto", "visual", "pain", "emotion"]
PROVIDER_CHOICES = ["image2low", "qw", "nanobanana", "og-image2", "dashscope"]
DEFAULT_PROFILE = "a-plus-standard-12"
DEFAULT_CATEGORY = "auto"
DEFAULT_CONVERSION_DRIVER = "auto"
DEFAULT_PROVIDER = "image2low"
DEFAULT_PROVIDER_MODELS = {
    "image2low": "og-image2-low",
    "og-image2": "og-image2-low",
    "qw": "qwen-image-2.0-pro",
    "dashscope": "qwen-image-2.0-pro",
    "nanobanana": "gemini-3.1-flash-image-preview",
}

# Legacy 7-section fallback for very old detail-plan.json files that have no
# `profile` field and rely on the historical hard-coded section list.
LEGACY_SECTIONS = [
    ("hero", "首屏展示商品系列、品牌识别和核心利益点"),
    ("selling-points", "核心卖点矩阵，使用卡片或图标组合"),
    ("quality-story", "品质、来源、工艺或可信证据"),
    ("product-focus", "单品特写和关键卖点"),
    ("scenario-proof", "使用场景、产地、使用方式或用户收益"),
    ("spec-table", "规格、成分、参数或购买前确认"),
    ("footer", "品牌收尾和信任感"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an Amazon A+ long-detail image (default 12 modules).")
    parser.add_argument("--product-name", required=True, help="商品名称")
    parser.add_argument("--images", nargs="+", required=True, help="商品参考图路径")
    parser.add_argument("--research", required=True, help="Agent 生成的 research.json")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--width", type=int, default=750, help="最终长图宽度")
    parser.add_argument("--model", default=None, help="生图模型；不传时按 --provider 使用默认模型")
    parser.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        default=DEFAULT_PROVIDER,
        help="生图通道；使用前应让用户选择 image2low / qw / nanobanana，默认 image2low",
    )
    parser.add_argument("--provider-size", default="1024x1024", help="传给底层 provider 的生图尺寸")
    parser.add_argument("--og-api-url", default=None, help="og-image2 OpenAI-compatible Base URL")
    parser.add_argument(
        "--og-public-reference",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="og-image2 使用公网 URL 串行图生图：上传输入图和每段输出图，再把公网 URL 传给下一段",
    )
    parser.add_argument("--plan", default=None, help="可选 detail-plan.json")
    parser.add_argument("--section-height", type=int, default=None, help="覆盖默认 section 高度")
    parser.add_argument("--transition-ratio", type=float, default=0.16, help="上一段底部裁切比例")
    parser.add_argument("--offline", action="store_true", help="离线占位模式，不调用生图 API")
    parser.add_argument("--og-timeout", type=int, default=600, help="og-image2 单次 HTTP 请求超时时间（秒）")

    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default=DEFAULT_PROFILE,
        help="A+ 长图 profile：默认 a-plus-standard-12（12 模块）",
    )
    parser.add_argument(
        "--category",
        choices=CATEGORY_CHOICES,
        default=DEFAULT_CATEGORY,
        help="商品品类，决定色板 / 场景 / 视觉表现；auto 表示由 detail-plan 自带或后续人工指定",
    )
    parser.add_argument(
        "--conversion-driver",
        choices=CONVERSION_DRIVER_CHOICES,
        default=DEFAULT_CONVERSION_DRIVER,
        help="转化驱动力：visual / pain / emotion；auto 由 plan 决定",
    )
    parser.add_argument(
        "--english-baseline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否以英文 baseline 写 on-image 文案（默认开启）",
    )
    parser.add_argument("--style-lock", default=None, help="外部 style-lock.json 路径")
    parser.add_argument("--buyer-reason-card", default=None, help="外部 buyer-reason-card.json 路径")
    parser.add_argument("--scorecard", default=None, help="外部 self-review scorecard JSON 路径")
    parser.add_argument(
        "--product-type-template",
        default="auto",
        help="商品类型叙事模板；auto 表示按商品名、品类和 research 自动识别",
    )
    parser.add_argument(
        "--with-angle-sheet",
        action="store_true",
        help="生成 Product Angle Sheet（白底图之后、首段之前）",
    )
    return parser.parse_args()


def resolve_generation_provider(args: argparse.Namespace) -> argparse.Namespace:
    provider = args.provider
    if provider == "image2low":
        args.provider_kind = "og-image2"
    elif provider == "qw":
        args.provider_kind = "dashscope"
    else:
        args.provider_kind = provider

    if not args.model:
        args.model = DEFAULT_PROVIDER_MODELS[provider]
    return args


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_load_json(path: Path | None, default: Any = None) -> Any:
    if path is None:
        return default
    target = Path(path)
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default


def validate_inputs(args: argparse.Namespace) -> tuple[list[Path], Path, Path]:
    images = [Path(item) for item in args.images]
    missing = [str(path) for path in images if not path.exists()]
    if missing:
        raise FileNotFoundError(f"商品图不存在: {missing}")
    research = Path(args.research)
    if not research.exists():
        raise FileNotFoundError(f"research.json 不存在: {research}")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    return images, research, output


def load_profile_templates() -> dict:
    if not PROFILE_TEMPLATES_PATH.exists():
        return {"profiles": {}}
    return load_json(PROFILE_TEMPLATES_PATH)


def load_category_profile(category: str) -> dict:
    if category == "auto" or not CATEGORY_PROFILES_PATH.exists():
        return {}
    data = load_json(CATEGORY_PROFILES_PATH)
    return data.get("categories", {}).get(category, {})


def load_product_type_templates() -> dict:
    if not PRODUCT_TYPE_TEMPLATES_PATH.exists():
        return {"templates": {}}
    return load_json(PRODUCT_TYPE_TEMPLATES_PATH)


def _research_text(research: dict) -> str:
    values: list[str] = []
    for key in ("product_name", "brand", "category", "marketplace"):
        value = research.get(key)
        if value:
            values.append(str(value))
    for key in ("selling_points", "target_buyers", "usage_scenarios", "missing_facts", "risk_notes"):
        value = research.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    for item in research.get("verified_facts", []):
        if isinstance(item, dict):
            values.append(str(item.get("claim", "")))
        else:
            values.append(str(item))
    specs = research.get("specs")
    if isinstance(specs, dict):
        values.extend(str(value) for value in specs.values())
    return " ".join(values).lower()


def resolve_product_type_template(
    *,
    requested: str,
    category: str,
    product_name: str,
    research: dict,
    templates: dict,
) -> tuple[str | None, dict]:
    all_templates = templates.get("templates", {})
    if requested and requested != "auto":
        template = all_templates.get(requested)
        return (requested, dict(template)) if template else (None, {})

    haystack = f"{product_name} {_research_text(research)}".lower()
    effective_category = category if category != "auto" else str(research.get("category") or "auto")
    best_id: str | None = None
    best_score = 0
    for template_id, template in all_templates.items():
        if template.get("category") not in {None, "", effective_category, "auto"}:
            continue
        score = 0
        for keyword in template.get("trigger_keywords", []):
            if str(keyword).lower() in haystack:
                score += 1
        if score > best_score:
            best_id = template_id
            best_score = score

    if best_id and best_score >= 2:
        return best_id, dict(all_templates.get(best_id, {}))
    return None, {}


def apply_product_type_template_sections(
    sections: list[dict],
    product_type_template: dict,
    profile: str,
) -> list[dict]:
    profile_sections = product_type_template.get("profiles", {}).get(profile)
    if not profile_sections:
        return sections
    return [dict(section) for section in profile_sections]


def collect_og_reference_urls(*urls: str | None, max_items: int = 3) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        ordered.append(url)
        if len(ordered) >= max_items:
            break
    return ordered


def resolve_profile_sections(profile: str, templates: dict) -> tuple[list[dict], int, int]:
    profiles = templates.get("profiles", {})
    if profile in profiles:
        spec = profiles[profile]
        sections = list(spec.get("sections", []))
        section_height = spec.get("section_height") or 620
        overlap = spec.get("transition_overlap_px", 40)
        return sections, section_height, overlap
    # legacy fallback
    sections = [
        {
            "id": section_id,
            "module": 0,
            "goal": goal,
            "frame_objective": goal,
            "prompt_focus": goal,
            "transition_in": "承接上一段的背景色、纸纹和品牌装饰元素",
            "transition_out": "底部 15% 保留可延展的渐变背景和装饰线稿",
            "shared_elements": ["品牌色带", "细线装饰", "柔和纸纹"],
        }
        for section_id, goal in LEGACY_SECTIONS
    ]
    return sections, 620, 40


def build_default_image_copy_gate(category_profile: dict, section: dict, english_baseline: bool) -> dict:
    headline_directions = category_profile.get("headline_directions") or []
    headline = headline_directions[0] if headline_directions else "Premium Everyday Choice"
    return {
        "headline_en": headline if english_baseline else "",
        "headline_localized": None,
        "support_labels": ["Quality crafted", "Daily ready", "Trusted choice"],
        "proof_line": "",
        "cta": "soft CTA",
    }


def build_style_lock(
    category: str,
    category_profile: dict,
    conversion_driver: str,
    product_name: str,
) -> dict:
    palette = category_profile.get("palette") or ["#f5f6f8", "#1f2933", "#d6cfc4", "#3b6cf6"]
    accent = category_profile.get("accent") or "#3b6cf6"
    temperature = category_profile.get("temperature") or "neutral"
    lighting = category_profile.get("lighting") or "clean studio lighting with gentle shadows"
    background = ", ".join(category_profile.get("scenes") or ["clean studio with subtle category cues"])
    ornaments = ", ".join(category_profile.get("ornaments") or ["thin-line icons", "rounded info cards"])
    keywords = ", ".join(category_profile.get("keywords") or ["premium", "clean", "modern"])

    visual_direction = f"premium amazon a+ visual system tuned for {category if category != 'auto' else 'this product'} ({keywords})"
    summary_lines = [
        f"Campaign Style Lock for {product_name}: consistent premium Amazon A+ visual system across all sections;",
        f"visual direction: {visual_direction};",
        f"fixed palette: {', '.join(palette)} with accent {accent};",
        f"temperature: {temperature};",
        "font system: modern geometric sans-serif headline placeholders only, concise labels;",
        f"background system: {background};",
        f"lighting system: {lighting};",
        "layout system: rounded info cards, generous whitespace, consistent label hierarchy, clear vertical rhythm;",
        f"icon system: {ornaments};",
        "product presentation: stable scale and placement, premium product photography, no logo or package distortion;",
        "consistency requirements: fixed palette, single font system, stable backgrounds, consistent lighting, matched icon styles;",
        f"conversion driver bias: {conversion_driver}.",
    ]
    summary = " ".join(summary_lines)
    summary_hash = hashlib.sha1(summary.encode("utf-8")).hexdigest()
    return {
        "visual_direction": visual_direction,
        "palette": palette,
        "accent": accent,
        "temperature": temperature,
        "font_system": "modern geometric sans-serif headline placeholders only",
        "background_system": background,
        "lighting_system": lighting,
        "layout_system": "rounded info cards, generous whitespace, consistent label hierarchy",
        "icon_system": ornaments,
        "product_presentation": "stable scale and placement, premium product photography",
        "consistency_requirements": "fixed palette, single font system, stable backgrounds, consistent lighting, matched icon styles",
        "summary": summary,
        "summary_hash": summary_hash,
    }


def default_buyer_reason_card(product_name: str, research: dict, category_profile: dict) -> dict:
    headline_directions = category_profile.get("headline_directions") or []
    primary = headline_directions[0] if headline_directions else f"Choose {product_name} for daily quality"
    proof_candidates = [item.get("claim", "") for item in research.get("verified_facts", []) if isinstance(item, dict)]
    return {
        "target_buyer": "Awaiting agent input — replace with concrete buyer description",
        "purchase_trigger": "Awaiting agent input — describe why now",
        "belief_shift": "Awaiting agent input — from old belief to new belief",
        "primary_selling_reason": primary,
        "proof_material": proof_candidates[0] if proof_candidates else "proof placeholder",
        "review_recommendation_material": "skip until real review supplied (Review Compliance Switch)",
        "offer_lever": "guarantee / bundle / risk reversal — supply when known",
        "evidence_bound_claims": proof_candidates[:3],
        "source_labels": {"primary_selling_reason": "Default", "proof_material": "Default"},
    }


def default_scorecard() -> dict:
    keys = [
        "conversion_clarity",
        "buyer_reason_fit",
        "english_baseline_quality",
        "mobile_readability",
        "visual_consistency",
        "platform_fit",
        "evidence_honesty",
    ]
    return {key: "na" for key in keys}


def build_default_plan(
    product_name: str,
    research: dict,
    width: int,
    profile: str,
    category: str,
    conversion_driver: str,
    english_baseline: bool,
    templates: dict,
    category_profile: dict,
    product_type_template_id: str | None,
    product_type_template: dict,
) -> tuple[dict, int, int]:
    sections, section_height, overlap = resolve_profile_sections(profile, templates)
    sections = apply_product_type_template_sections(sections, product_type_template, profile)

    palette = category_profile.get("palette") or ["#12346b", "#c9a557", "#f7f4ec", "#1f2933"]
    accent = category_profile.get("accent") or "#3b6cf6"
    typography = "modern geometric sans-serif headline placeholders only"
    background_texture = ", ".join(category_profile.get("scenes") or ["clean studio with subtle category cues"])
    ornaments = ", ".join(category_profile.get("ornaments") or ["thin-line icons", "rounded info cards"])

    verified = [item.get("claim", "") for item in research.get("verified_facts", []) if isinstance(item, dict)]
    review = list(research.get("missing_facts", [])) + list(research.get("risk_notes", []))

    enriched_sections = []
    for idx, base in enumerate(sections):
        next_color = palette[(idx + 1) % len(palette)]
        current_color = palette[idx % len(palette)]
        section = dict(base)
        section.setdefault("bg_color_top", current_color)
        section.setdefault("bg_color_bottom", next_color)
        section.setdefault("claims_allowed", verified[:3])
        section.setdefault("claims_for_review", review)
        section.setdefault("image_copy_gate", build_default_image_copy_gate(category_profile, section, english_baseline))
        section.setdefault(
            "category_hint",
            {
                "palette": category_profile.get("palette", []),
                "accent": category_profile.get("accent", ""),
                "scenes": category_profile.get("scenes", []),
                "ornaments": category_profile.get("ornaments", []),
                "headline_directions": category_profile.get("headline_directions", []),
            },
        )
        section.setdefault("assumptions_used", [])
        # Single-modules profile carries a per-section size string already.
        if base.get("size"):
            section["size"] = base["size"]
        enriched_sections.append(section)

    plan = {
        "product_name": product_name,
        "profile": profile,
        "category": category,
        "product_type_template": product_type_template_id,
        "product_type_narrative": {
            "label": product_type_template.get("label"),
            "narrative_core": product_type_template.get("narrative_core"),
            "shopper_tension": product_type_template.get("shopper_tension"),
            "visual_principles": product_type_template.get("visual_principles", []),
        } if product_type_template_id else None,
        "conversion_driver": conversion_driver,
        "english_baseline": english_baseline,
        "canvas": {"width": width, "style": "Amazon A+ premium long detail"},
        "global_visual": {
            "palette": palette,
            "accent": accent,
            "typography": typography,
            "background_texture": background_texture,
            "ornaments": ornaments,
            "transition_overlap_px": overlap,
        },
        "sections": enriched_sections,
        "assumptions_used": [],
    }
    return plan, section_height, overlap


def normalize_existing_plan(
    plan: dict,
    args: argparse.Namespace,
    templates: dict,
    category_profile: dict,
) -> tuple[dict, int, int]:
    """Backfill missing fields on a user-supplied detail-plan.json.

    Plans without `profile` are treated as legacy-long-7 to preserve old behavior.
    """

    plan.setdefault("profile", "legacy-long-7" if "profile" not in plan else plan["profile"])
    plan.setdefault("category", args.category)
    plan.setdefault("conversion_driver", args.conversion_driver)
    plan.setdefault("english_baseline", args.english_baseline)
    plan.setdefault("canvas", {"width": args.width, "style": "Amazon A+ premium long detail"})
    plan.setdefault("global_visual", {})
    plan.setdefault("assumptions_used", [])

    profile = plan["profile"]
    profiles = templates.get("profiles", {})
    overlap = profiles.get(profile, {}).get("transition_overlap_px", plan["global_visual"].get("transition_overlap_px", 40))
    section_height = profiles.get(profile, {}).get("section_height") or 620
    plan["global_visual"]["transition_overlap_px"] = overlap

    for section in plan.get("sections", []):
        section.setdefault("frame_objective", section.get("goal", ""))
        section.setdefault("prompt_focus", section.get("goal", ""))
        section.setdefault("image_copy_gate", build_default_image_copy_gate(category_profile, section, plan["english_baseline"]))
        section.setdefault("category_hint", {
            "palette": category_profile.get("palette", []),
            "accent": category_profile.get("accent", ""),
            "scenes": category_profile.get("scenes", []),
            "ornaments": category_profile.get("ornaments", []),
            "headline_directions": category_profile.get("headline_directions", []),
        })
        section.setdefault("assumptions_used", [])

    return plan, section_height, overlap


def write_prompt(
    *,
    product_name: str,
    section: dict,
    index: int,
    width: int,
    white_path: Path,
    product_images: list[Path],
    previous_crop: Path | None,
    previous_crop_ref: str | None,
    prompts_dir: Path,
    style_lock: dict,
    buyer_reason: dict,
    angle_sheet_url: str | None,
    profile: str,
    identity_first_refs: bool,
) -> Path:
    section_id = section.get("id", f"section-{index + 1}")
    is_first = index == 0
    is_last_hint = section.get("module") == 12 or section_id in {"closing", "footer"}
    style_block = style_lock.get("summary") or "Campaign Style Lock: consistent premium Amazon A+ visual system across all sections."

    primary_reason = buyer_reason.get("primary_selling_reason") or "(supply primary selling reason)"
    belief_from = buyer_reason.get("target_buyer", "current shopper belief")
    belief_to = buyer_reason.get("belief_shift") or "the new belief this image should establish"

    copy_gate = section.get("image_copy_gate") or {}
    headline = copy_gate.get("headline_en") or "(headline ≤ 8 words)"
    if not headline and copy_gate.get("headline_localized"):
        headline = copy_gate["headline_localized"]
    support_labels = copy_gate.get("support_labels") or []
    proof_line = copy_gate.get("proof_line") or ""
    cta = copy_gate.get("cta") or "omitted"

    category_hint = section.get("category_hint") or {}
    palette_hint = ", ".join(category_hint.get("palette") or [])
    scene_hint = ", ".join(category_hint.get("scenes") or [])
    ornament_hint = ", ".join(category_hint.get("ornaments") or [])

    frame_objective = section.get("frame_objective") or section.get("goal") or section_id
    prompt_focus = section.get("prompt_focus") or section.get("goal") or ""
    story_role = section.get("story_role") or ""
    shopper_tension = section.get("shopper_tension") or ""
    visual_moment = section.get("visual_moment") or ""
    must_show = section.get("must_show") or []
    header = f"Generate section {index + 1:02d} ({section_id}) of an Amazon A+ long-detail page for {product_name}.\n"
    if section.get("size"):
        target_size_line = f"Target size: {section['size']} (single-module profile).\n"
    else:
        target_size_line = f"Target width: {width}px; section height around {section.get('height', '420-620')}px.\n"

    style_block_text = f"[Style Lock]\n{style_block}\n"
    buyer_block = (
        "[Buyer Reason]\n"
        f"Primary Selling Reason: {primary_reason}\n"
        f"Belief Shift: from {belief_from} to {belief_to}\n"
    )
    copy_block = (
        "[Image Copy Gate]\n"
        f'Headline: "{headline}"\n'
        f"Support labels: {support_labels if support_labels else 'none'}\n"
        f"Proof line: {proof_line if proof_line else 'omitted'}\n"
        f"CTA: {cta}\n"
        "Render text as clean layout with short readable headline placeholders, concise labels only.\n"
    )

    refs_lines: list[str] = []
    if previous_crop is not None and not identity_first_refs:
        transition_ref = previous_crop_ref or str(previous_crop)
        refs_lines.append(
            f"Reference image 1: previous-section bottom crop at {transition_ref}. Use it only to sample color, lighting, background gradient, and subtle texture for the top seam-safe band. Do not copy or repeat its text, cards, product, icons, layout, or foreground elements."
        )
        refs_lines.append(f"Reference image 2: white-background product image at {white_path}.")
        refs_lines.append(f"Reference image 3: original product photo at {product_images[0]}.")
    elif previous_crop is not None:
        transition_ref = previous_crop_ref or str(previous_crop)
        refs_lines.append(f"Reference image 1: white-background product image at {white_path}.")
        refs_lines.append(f"Reference image 2: original product photo at {product_images[0]} for exact product identity.")
        refs_lines.append(
            f"Reference image 3: previous-section bottom crop at {transition_ref}. Use it only to sample color, lighting, background gradient, and subtle texture for the top seam-safe band. Do not copy or repeat its text, cards, product, icons, layout, or foreground elements."
        )
    else:
        refs_lines.append(f"Reference image 1: white-background product image at {white_path}.")
        refs_lines.append(f"Reference image 2: original product photo at {product_images[0]} for package detail.")
    if angle_sheet_url:
        refs_lines.append(f"Reference image 4: product angle sheet (identity reference only) at {angle_sheet_url}.")

    identity_block = (
        "[Product Identity Lock]\n"
        f"The product must remain the same SKU as the original product reference in every section. Preserve the real {product_name} identity: same silhouette, key structures, proportions, color family, material feel, visible controls, package shape, and distinctive product details.\n"
        "Use the white-background product image and original product photo as the strongest identity anchors. The previous-section crop is only for seam background continuity, never for product shape, layout, or feature invention.\n"
        "If the section needs hands, people, pets, props, bags, car holders, lanyards, diagrams, or scenes, place the same product into that scene; do not redesign it into a generic product or a different accessory.\n"
    )

    section_block = (
        "[Section Frame]\n"
        f"Frame objective: {frame_objective}\n"
        f"Section focus: {prompt_focus}\n"
        f"Story role: {story_role if story_role else 'section-specific selling job'}\n"
        f"Shopper tension: {shopper_tension if shopper_tension else 'make the user problem concrete'}\n"
        f"Visual moment: {visual_moment if visual_moment else 'show a distinct, product-relevant moment'}\n"
        f"Must show: {must_show if must_show else 'visible product and one clear benefit'}\n"
        f"Category cues: palette {palette_hint or 'use Style Lock palette'}; scenes {scene_hint or 'category-appropriate'}; props {ornament_hint or 'minimal premium props'}.\n"
        "Do not reuse the same generic lifestyle scene from other sections. This section must have its own distinct composition, camera angle, and selling job.\n"
        + "\n".join(refs_lines)
        + "\n"
    )

    closing_extra = ""
    if is_last_hint:
        closing_extra = "Final emotional headline only; do not pile new selling points.\n"

    constraints_block = (
        "[Seam-Safe Contract & Constraints]\n"
        "Top seam-safe band: keep the top 18-20% as background-only continuity. It may contain only gradient, plain color, soft lighting, paper/grain texture, or very faint abstract ornament.\n"
        "Bottom seam-safe band: keep the bottom 18-20% as background-only handoff for the next section. It may contain only gradient, plain color, soft lighting, paper/grain texture, or very faint abstract ornament.\n"
        "Never place text, numbers, labels, cards, logos, product bodies, packaging, spec tables, human faces, hands, icons, arrows, hard divider lines, or foreground objects inside either seam-safe band.\n"
        "Keep all section-specific content in the middle safe area with clear padding away from both seam-safe bands.\n"
        "Avoid: hard cut lines, sudden background jumps, repeated previous-section content, invented claims, fake certifications, package/logo changes, generic-stock vibe, cheap Taobao layout, unreadable small text.\n"
        f"{closing_extra}"
    )
    if angle_sheet_url:
        constraints_block += "Use the product angle sheet only as product identity reference.\n"

    prompt = (
        f"{header}{target_size_line}{style_block_text}{buyer_block}{copy_block}{identity_block}{section_block}{constraints_block}"
    )

    path = prompts_dir / f"step-{index + 1:02d}-{section_id}.txt"
    path.write_text(prompt, encoding="utf-8")
    return path


def _parse_hex_color(value: str, fallback: tuple[int, int, int] = (200, 200, 200)) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return fallback
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return fallback
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return fallback


def make_placeholder(path: Path, width: int, height: int, label: str, top: str, bottom: str) -> None:
    top_rgb = _parse_hex_color(top, (240, 240, 240))
    bottom_rgb = _parse_hex_color(bottom, (200, 200, 200))
    image = Image.new("RGB", (width, height), top_rgb)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(round(a * (1 - t) + b * t) for a, b in zip(top_rgb, bottom_rgb))
        draw.line([(0, y), (width, y)], fill=color)
    draw.rectangle((40, 40, width - 40, height - 40), outline="#ffffff", width=4)
    draw.text((60, 70), label, fill="#ffffff")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def run_generate(script: Path, args: list[str]) -> dict:
    last_output = ""
    for attempt in range(4):
        completed = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
        last_output = f"{completed.stdout}\n{completed.stderr}"
        if completed.returncode == 0:
            break
        if (
            "Throttling.RateQuota" in last_output
            or "RequestLimitExceeded" in last_output
            or "maximum concurrency" in last_output
            or "rate limit" in last_output.lower()
            or "Read timed out" in last_output
            or "read timeout" in last_output.lower()
        ):
            time.sleep(45 * (attempt + 1))
            continue
        raise RuntimeError(f"generate.py failed: {completed.stdout}\n{completed.stderr}")
    else:
        raise RuntimeError(f"generate.py failed after retries: {last_output}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"generate.py did not return JSON: {completed.stdout}") from exc


def normalize_generated_image(source: Path, target: Path, width: int, height: int) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        scale = max(width / image.width, height / image.height)
        resized = image.resize(
            (max(width, round(image.width * scale)), max(height, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
        left = max(0, (resized.width - width) // 2)
        top = max(0, (resized.height - height) // 2)
        cropped = resized.crop((left, top, left + width, top + height))
        target.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(target)


def find_raw_step_file(step_path: Path) -> Path | None:
    candidates = sorted(step_path.parent.glob(f"{step_path.stem}_*"))
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return candidate
    return None


def max_step_source_width(steps_dir: Path) -> int | None:
    widths = []
    for path in sorted(steps_dir.glob("step-*_*")):
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        try:
            with Image.open(path) as image:
                widths.append(image.width)
        except Exception:
            continue
    return max(widths) if widths else None


def run_compose(
    *,
    compose_script: Path,
    steps_dir: Path,
    output: Path,
    width: int,
    review_file: Path,
    manifest: Path | None = None,
    source: str = "raw",
    compose_mode: str = "stack",
    overlap: int = 0,
    blend_mode: str = "gaussian",
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(compose_script),
        "--input",
        str(steps_dir),
        "--output",
        str(output),
        "--width",
        str(width),
        "--source",
        source,
        "--compose-mode",
        compose_mode,
        "--overlap",
        str(overlap),
        "--blend-mode",
        blend_mode,
        "--review-file",
        str(review_file),
    ]
    if manifest is not None:
        command.extend(["--manifest", str(manifest)])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"compose_long_image.py failed: {completed.stdout}\n{completed.stderr}")
    return json.loads(completed.stdout)


def upload_tmpfiles(path: Path) -> str:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("缺少 requests，无法上传公网参考图") from exc

    last_error = ""
    for attempt in range(3):
        try:
            with path.open("rb") as handle:
                response = requests.post(
                    "https://tmpfiles.org/api/v1/upload",
                    files={"file": (path.name, handle)},
                    timeout=120,
                )
            data = response.json()
            if response.status_code < 400 and data.get("status") == "success":
                page_url = data["data"]["url"]
                return page_url.replace("http://tmpfiles.org/", "https://tmpfiles.org/dl/")
            last_error = response.text
        except Exception as exc:
            last_error = str(exc)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"上传公网参考图失败: {path}: {last_error}")


def generator_call(
    args: argparse.Namespace,
    dashscope_script: Path,
    og_script: Path,
    nanobanana_script: Path,
    *,
    images: list[str],
    prompt: str,
    output_dir: Path,
    prefix: str,
    image_urls: list[str] | None = None,
    provider_size: str | None = None,
) -> dict:
    if args.provider_kind == "og-image2":
        og_args = [
            "--model",
            args.model,
            "--prompt",
            prompt,
            "--size",
            provider_size or args.provider_size or "1024x1024",
            "--output",
            str(output_dir),
            "--prefix",
            prefix,
        ]
        if args.og_api_url:
            og_args.extend(["--api-url", args.og_api_url])
        for image_url in image_urls or []:
            og_args.extend(["--image", image_url])
        og_args.extend(["--timeout", str(args.og_timeout)])
        return run_generate(og_script, og_args)

    if args.provider_kind == "nanobanana":
        return run_generate(
            nanobanana_script,
            [
                "--model",
                args.model,
                "--images",
                *images,
                "--prompt",
                prompt,
                "--output",
                str(output_dir),
                "--prefix",
                prefix,
                "--timeout",
                str(args.og_timeout),
            ],
        )

    return run_generate(
        dashscope_script,
        [
            "--model",
            args.model,
            "--images",
            *images,
            "--prompt",
            prompt,
            "--size",
            provider_size or args.provider_size or f"{args.width}x620",
            "--output",
            str(output_dir),
            "--prefix",
            prefix,
            "--json-result",
        ],
    )


def crop_transition(source: Path, output: Path, ratio: float) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        height = max(1, round(image.height * ratio))
        crop = image.crop((0, image.height - height, image.width, image.height))
        output.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output)


def maybe_generate_angle_sheet(
    *,
    args: argparse.Namespace,
    product_images: list[Path],
    output_dir: Path,
    style_lock: dict,
    buyer_reason: dict,
    public_reference_urls: list[str],
    public_reference_records: list[dict[str, Any]],
    generate_script: Path,
    og_generate_script: Path,
    nanobanana_generate_script: Path,
) -> tuple[Path | None, str | None]:
    """Generate an optional Product Angle Sheet for identity reference."""

    if not args.with_angle_sheet:
        return None, None

    angle_dir = output_dir / "angle-sheet"
    angle_dir.mkdir(parents=True, exist_ok=True)
    angle_path = angle_dir / "angle-sheet.png"

    style_summary = style_lock.get("summary") or ""
    primary_reason = buyer_reason.get("primary_selling_reason", "")
    angle_prompt = (
        f"Build a temporary Product Angle Sheet for {args.product_name}. Identity reference only.\n"
        "Goal: lock product identity (shape, material, logo, package, color, key components) for downstream A+ sections.\n"
        "Show the same product across 6-8 angles on a clean light studio background:\n"
        "- front view\n"
        "- left 45 degree view\n"
        "- right 45 degree view\n"
        "- side / thickness view\n"
        "- back / magnetic view\n"
        "- key structural detail (port / button / LED / closure)\n"
        "- product + package combo (if applicable)\n"
        "- one usage angle (if relevant to the category)\n"
        "Layout: clean grid or row arrangement with consistent perspective and lighting. No promotional badges, no price tags, no rating, no Bestseller marks, no marketing copy.\n"
        "Strip any logos / sale stickers / overlays from the reference photo. Preserve real package text faithfully.\n"
        f"[Style Lock context, do not copy verbatim]\n{style_summary}\n"
        f"[Identity bias]\nPrimary product story: {primary_reason}\n"
    )

    if angle_path.exists():
        if args.provider_kind == "og-image2" and args.og_public_reference and not args.offline:
            url = upload_tmpfiles(angle_path)
            public_reference_records.append({"stage": "angle-sheet", "file": str(angle_path), "url": url})
            return angle_path, url
        return angle_path, None

    if args.offline:
        make_placeholder(
            angle_path,
            args.width,
            args.section_height or 620,
            "angle-sheet",
            "#f4efe8",
            "#dcd6cb",
        )
        return angle_path, None

    result = generator_call(
        args,
        generate_script,
        og_generate_script,
        nanobanana_generate_script,
        images=[str(path) for path in product_images],
        prompt=angle_prompt,
        output_dir=angle_dir,
        prefix="angle-sheet",
        image_urls=public_reference_urls,
    )
    if result.get("files"):
        generated = Path(result["files"][0])
        if generated != angle_path:
            normalize_generated_image(generated, angle_path, args.width, args.section_height or 620)

    angle_url = None
    if args.provider_kind == "og-image2" and args.og_public_reference:
        angle_url = upload_tmpfiles(angle_path)
        public_reference_records.append({"stage": "angle-sheet", "file": str(angle_path), "url": angle_url})
    return angle_path, angle_url


def main() -> None:
    args = resolve_generation_provider(parse_args())
    product_images, research_path, output_dir = validate_inputs(args)
    research = load_json(research_path)

    templates = load_profile_templates()
    product_type_templates = load_product_type_templates()
    plan_path = Path(args.plan) if args.plan else output_dir / "detail-plan.json"
    if plan_path.exists():
        plan = load_json(plan_path)
        effective_category = args.category if args.category != "auto" else plan.get("category", args.category)
        if args.category != "auto":
            plan["category"] = args.category
        if args.conversion_driver != "auto":
            plan["conversion_driver"] = args.conversion_driver
        category_profile = load_category_profile(effective_category)
        product_type_template_id, product_type_template = resolve_product_type_template(
            requested=args.product_type_template,
            category=effective_category,
            product_name=args.product_name,
            research=research,
            templates=product_type_templates,
        )
        plan.setdefault("product_type_template", product_type_template_id)
        if product_type_template_id:
            plan.setdefault(
                "product_type_narrative",
                {
                    "label": product_type_template.get("label"),
                    "narrative_core": product_type_template.get("narrative_core"),
                    "shopper_tension": product_type_template.get("shopper_tension"),
                    "visual_principles": product_type_template.get("visual_principles", []),
                },
            )
        plan, section_height, overlap = normalize_existing_plan(plan, args, templates, category_profile)
    else:
        category_profile = load_category_profile(args.category)
        product_type_template_id, product_type_template = resolve_product_type_template(
            requested=args.product_type_template,
            category=args.category,
            product_name=args.product_name,
            research=research,
            templates=product_type_templates,
        )
        plan, section_height, overlap = build_default_plan(
            product_name=args.product_name,
            research=research,
            width=args.width,
            profile=args.profile,
            category=args.category,
            conversion_driver=args.conversion_driver,
            english_baseline=args.english_baseline,
            templates=templates,
            category_profile=category_profile,
            product_type_template_id=product_type_template_id,
            product_type_template=product_type_template,
        )

    if args.section_height is not None:
        section_height = args.section_height

    if args.style_lock:
        style_lock = safe_load_json(Path(args.style_lock), default=None) or build_style_lock(
            plan["category"], category_profile, plan["conversion_driver"], args.product_name
        )
    else:
        style_lock_file = output_dir / "style-lock.json"
        if style_lock_file.exists():
            style_lock = load_json(style_lock_file)
        else:
            style_lock = build_style_lock(plan["category"], category_profile, plan["conversion_driver"], args.product_name)
            style_lock_file.write_text(json.dumps(style_lock, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.buyer_reason_card:
        buyer_reason = safe_load_json(Path(args.buyer_reason_card), default=None) or default_buyer_reason_card(
            args.product_name, research, category_profile
        )
    else:
        buyer_file = output_dir / "buyer-reason-card.json"
        if buyer_file.exists():
            buyer_reason = load_json(buyer_file)
        else:
            buyer_reason = default_buyer_reason_card(args.product_name, research, category_profile)
            buyer_file.write_text(json.dumps(buyer_reason, ensure_ascii=False, indent=2), encoding="utf-8")

    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts_dir = output_dir / "prompts"
    steps_dir = output_dir / "steps"
    transitions_dir = output_dir / "transitions"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)
    transitions_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    generate_script = script_dir / "generate.py"
    og_generate_script = script_dir.parents[3] / "scripts" / "og-image2" / "generate.py"
    nanobanana_generate_script = script_dir.parents[3] / "scripts" / "image-gemini-nanobanana" / "generate.py"
    compose_script = script_dir / "compose_long_image.py"

    original_public_url: str | None = None
    white_public_url: str | None = None
    previous_step_public_url: str | None = None
    public_reference_records: list[dict[str, Any]] = []
    if args.provider_kind == "og-image2" and args.og_public_reference and not args.offline:
        original_public_url = upload_tmpfiles(product_images[0])
        public_reference_records.append(
            {"stage": "input-product", "file": str(product_images[0]), "url": original_public_url}
        )

    white_path = output_dir / "00-white-background.png"
    if white_path.exists():
        if args.provider_kind == "og-image2" and args.og_public_reference and not args.offline:
            white_public_url = upload_tmpfiles(white_path)
            public_reference_records.append(
                {"stage": "00-white-background", "file": str(white_path), "url": white_public_url}
            )
    elif args.offline:
        make_placeholder(white_path, args.width, section_height, "00-white-background", "#f8f8f8", "#ffffff")
    else:
        white_prompt = (
            "Create a clean white-background product image. Preserve package, logo, shape, "
            "and visible product identity. Do not invent claims. Product: "
            f"{args.product_name}."
        )
        white_result = generator_call(
            args,
            generate_script,
            og_generate_script,
            nanobanana_generate_script,
            images=[str(path) for path in product_images],
            prompt=white_prompt,
            output_dir=output_dir,
            prefix="00-white-background",
            image_urls=collect_og_reference_urls(original_public_url),
        )
        if white_result.get("files"):
            generated = Path(white_result["files"][0])
            if generated != white_path:
                normalize_generated_image(generated, white_path, args.width, section_height)
        if args.provider_kind == "og-image2" and args.og_public_reference:
            white_public_url = upload_tmpfiles(white_path)
            public_reference_records.append(
                {"stage": "00-white-background", "file": str(white_path), "url": white_public_url}
            )

    angle_sheet_path, angle_sheet_url = maybe_generate_angle_sheet(
        args=args,
        product_images=product_images,
        output_dir=output_dir,
        style_lock=style_lock,
        buyer_reason=buyer_reason,
        public_reference_urls=collect_og_reference_urls(white_public_url, original_public_url),
        public_reference_records=public_reference_records,
        generate_script=generate_script,
        og_generate_script=og_generate_script,
        nanobanana_generate_script=nanobanana_generate_script,
    )

    previous_step: Path | None = None
    previous_crop: Path | None = None
    previous_crop_public_url: str | None = None
    step_records = []
    is_single_modules = plan.get("profile") == "single-modules"

    for idx, section in enumerate(plan["sections"]):
        section_id = section.get("id", f"section-{idx + 1}")
        if previous_step is not None and not is_single_modules:
            previous_crop = transitions_dir / f"transition-{idx:02d}-to-{idx + 1:02d}.png"
            crop_transition(previous_step, previous_crop, args.transition_ratio)
            if args.provider_kind == "og-image2" and args.og_public_reference and not args.offline:
                previous_crop_public_url = upload_tmpfiles(previous_crop)
                public_reference_records.append(
                    {
                        "stage": f"transition-{idx:02d}-to-{idx + 1:02d}",
                        "file": str(previous_crop),
                        "url": previous_crop_public_url,
                    }
                )
        else:
            previous_crop = None
            previous_crop_public_url = None

        prompt_path = write_prompt(
            product_name=args.product_name,
            section=section,
            index=idx,
            width=args.width,
            white_path=white_path,
            product_images=product_images,
            previous_crop=previous_crop,
            previous_crop_ref=previous_crop_public_url,
            prompts_dir=prompts_dir,
            style_lock=style_lock,
            buyer_reason=buyer_reason,
            angle_sheet_url=angle_sheet_url,
            profile=plan.get("profile", DEFAULT_PROFILE),
            identity_first_refs=args.provider_kind != "og-image2",
        )

        target_section_height = section_height
        target_width = args.width
        provider_size_override = None
        if section.get("size"):
            try:
                w_str, h_str = section["size"].split("x")
                target_width = int(w_str)
                target_section_height = int(h_str)
                provider_size_override = section["size"]
            except Exception:
                pass

        step_path = steps_dir / f"step-{idx + 1:02d}-{section_id}.png"
        raw_step_path = find_raw_step_file(step_path)
        if step_path.exists():
            pass
        elif args.offline:
            make_placeholder(
                step_path,
                target_width,
                target_section_height,
                f"{idx + 1:02d} {section_id}",
                section.get("bg_color_top", "#12346b"),
                section.get("bg_color_bottom", "#f7f4ec"),
            )
        else:
            image_args = [str(white_path), str(product_images[0])]
            if previous_crop:
                if args.provider_kind == "og-image2":
                    image_args.insert(0, str(previous_crop))
                else:
                    image_args.append(str(previous_crop))
            if angle_sheet_path is not None:
                image_args.append(str(angle_sheet_path))
            result = generator_call(
                args,
                generate_script,
                og_generate_script,
                nanobanana_generate_script,
                images=image_args,
                prompt=prompt_path.read_text(encoding="utf-8"),
                output_dir=steps_dir,
                prefix=f"step-{idx + 1:02d}-{section_id}",
                image_urls=collect_og_reference_urls(
                    previous_crop_public_url,
                    white_public_url,
                    original_public_url,
                    angle_sheet_url,
                ),
                provider_size=provider_size_override,
            )
            if result.get("files"):
                raw_step_path = Path(result["files"][0])
                normalize_generated_image(raw_step_path, step_path, target_width, target_section_height)
        raw_step_path = raw_step_path if raw_step_path and raw_step_path.exists() else find_raw_step_file(step_path)
        if args.provider_kind == "og-image2" and args.og_public_reference and not args.offline:
            previous_step_public_url = upload_tmpfiles(step_path)
            public_reference_records.append(
                {"stage": section_id, "file": str(step_path), "url": previous_step_public_url}
            )
        previous_step = step_path
        step_records.append(
            {
                "section": section_id,
                "file": str(step_path),
                "raw_file": str(raw_step_path) if raw_step_path else None,
                "prompt_file": str(prompt_path),
                "width": target_width,
                "height": target_section_height,
            }
        )

    review_file = output_dir / "review_required.json"
    review_required = []
    for section in plan.get("sections", []):
        review_required.extend(section.get("claims_for_review", []))
    review_file.write_text(
        json.dumps({"review_required": sorted(set(map(str, review_required)))}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    scorecard = safe_load_json(Path(args.scorecard) if args.scorecard else None, default=None) or default_scorecard()

    assumptions_used = list(plan.get("assumptions_used", []))
    manifest_category = plan.get("category", args.category)
    manifest_conversion_driver = plan.get("conversion_driver", args.conversion_driver)
    if manifest_category == "auto":
        assumptions_used.append({"field": "category", "label": "Default", "reason": "category=auto, fallback to global palette"})
    if manifest_conversion_driver == "auto":
        assumptions_used.append({"field": "conversion_driver", "label": "Default", "reason": "conversion_driver=auto"})

    if is_single_modules:
        manifest = {
            "status": "success",
            "final_file": None,
            "width": None,
            "height": None,
            "single_modules": True,
            "steps": step_records,
            "module_sizes": [
                {"section": item["section"], "width": item["width"], "height": item["height"]}
                for item in step_records
            ],
            "warnings": [],
            "review_required": sorted(set(map(str, review_required))),
        }
    else:
        final_path = output_dir / "final-detail-long.png"
        manifest = run_compose(
            compose_script=compose_script,
            steps_dir=steps_dir,
            output=final_path,
            width=args.width,
            review_file=review_file,
            source="raw",
            compose_mode="stack",
            overlap=0,
            blend_mode="gaussian",
        )
        raw_max_width = max_step_source_width(steps_dir)
        if raw_max_width:
            raw_max_path = output_dir / "final-detail-long-raw-original-stacked.jpg"
            raw_max_manifest = output_dir / "manifest-raw-original-stacked.json"
            run_compose(
                compose_script=compose_script,
                steps_dir=steps_dir,
                output=raw_max_path,
                width=raw_max_width,
                review_file=review_file,
                manifest=raw_max_manifest,
                source="raw",
                compose_mode="stack",
                overlap=0,
                blend_mode="gaussian",
            )
            manifest["raw_original_stacked_file"] = str(raw_max_path)
            manifest["raw_original_stacked_manifest"] = str(raw_max_manifest)
            manifest["raw_original_stacked_width"] = raw_max_width

    manifest["profile"] = plan.get("profile", DEFAULT_PROFILE)
    manifest["category"] = manifest_category
    manifest["product_type_template"] = plan.get("product_type_template")
    manifest["product_type_narrative"] = plan.get("product_type_narrative")
    manifest["conversion_driver"] = manifest_conversion_driver
    manifest["english_baseline"] = plan.get("english_baseline", args.english_baseline)
    manifest["generation_provider"] = args.provider
    manifest["generation_provider_kind"] = args.provider_kind
    manifest["generation_model"] = args.model
    manifest["research"] = str(research_path)
    manifest["detail_plan"] = str(plan_path)
    manifest["white_background"] = str(white_path)
    manifest["buyer_reason_card"] = buyer_reason
    manifest["style_lock"] = style_lock
    manifest["style_lock_hash"] = style_lock.get("summary_hash")
    manifest["scorecard"] = scorecard
    manifest["assumptions_used"] = assumptions_used
    manifest["generated_steps"] = step_records
    if angle_sheet_path is not None:
        manifest["angle_sheet"] = {"file": str(angle_sheet_path), "url": angle_sheet_url}
    if public_reference_records:
        manifest["public_references"] = public_reference_records

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
