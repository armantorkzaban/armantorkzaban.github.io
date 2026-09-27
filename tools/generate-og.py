#!/usr/bin/env python3
"""
generate-og.py
Automated Open Graph (OG) Image Generator for armantorkzaban.github.io.
Generates crisp, branded 1200x630 social preview cards for blog posts.
Supports both Persian (RTL) and English (LTR), with custom featured images
or elegant editorial typography layouts.
"""

import os
import sys
import re
import base64
import html
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "_posts"
OG_DIR = REPO_ROOT / "assets" / "img" / "og"
AVATAR_PATH = REPO_ROOT / "assets" / "img" / "avatar.png"
FONTS_DIR = REPO_ROOT / "tools" / "fonts"

# Ensure output directory exists
OG_DIR.mkdir(parents=True, exist_ok=True)

# Encode avatar once
AVATAR_B64 = ""
if AVATAR_PATH.exists():
    with open(AVATAR_PATH, "rb") as f:
        AVATAR_B64 = base64.b64encode(f.read()).decode("utf-8")


def is_persian(text: str) -> bool:
    """Check if text contains Persian/Arabic characters."""
    return bool(re.search(r"[\u0600-\u06FF]", text))


def clean_markdown_to_plain_text(raw_text: str) -> str:
    """Clean markdown and HTML into natural plain text without rogue spaces or audio widgets."""
    text = raw_text

    # 1. Strip audio players and fallback messages
    text = re.sub(r"<audio[^>]*>[\s\S]*?</audio>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>[\s\S]*?(?:گوش دادن به این مقاله|Listen to this article)[\s\S]*?</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"&#9654;|\u25B6", "", text)

    # 2. Decode HTML entities
    text = html.unescape(text)

    # 3. Strip inline HTML tags without inserting spaces (preserves punctuation & word flow)
    inline_tags = r"</?(?:a|em|strong|b|i|span|code|small|sup|sub)[^>]*>"
    text = re.sub(inline_tags, "", text)

    # 4. Strip block HTML tags with space
    text = re.sub(r"<[^>]+>", " ", text)

    # 5. Strip markdown images
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)

    # 6. Convert markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)

    # 7. Strip Chirpy attributes like {: .shadow }
    text = re.sub(r"\{:[^}]+\}", " ", text)

    # 8. Strip code blocks
    text = re.sub(r"`{1,3}[^`]+`{1,3}", " ", text)

    # 9. Strip emphasis markers (_text_ or *text*) cleanly
    text = re.sub(r"(^|\s)[_*~]+([^_*\n~]+)[_*~]+(\s|$)", r"\1\2\3", text)
    text = re.sub(r"[_*~]", "", text)

    # 10. Strip blockquotes, headers, bullets
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[>+\-]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)

    # 11. Normalize whitespace while preserving Persian ZWNJ (\u200c)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n+", " ", text).strip()

    return text


def parse_post(file_path: Path):
    """Parse front matter and excerpt from a Jekyll post markdown file."""
    content = file_path.read_text(encoding="utf-8")

    # Match front matter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not fm_match:
        title = file_path.stem
        date_match = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", title)
        if date_match:
            title = date_match.group(1).replace("-", " ")
        body = content
        category = "general"
        custom_img = None
        desc = ""
    else:
        fm_text = fm_match.group(1)
        body = fm_match.group(2)

        # Title
        t_match = re.search(r"^title:\s*[\"']?(.*?)[\"']?\s*$", fm_text, re.M)
        if t_match:
            title = t_match.group(1).strip("\"'")
        else:
            title = file_path.stem
            date_match = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", title)
            if date_match:
                title = date_match.group(1).replace("-", " ")

        # Category
        cat_match = re.search(r"^categor(?:y|ies):\s*(?:\[(.*?)\]|[\"']?(.*?)[\"']?)\s*$", fm_text, re.M)
        if cat_match:
            category = (cat_match.group(1) or cat_match.group(2) or "general").split(",")[0].strip("\"' ")
        else:
            category = "general"

        # Explicit image in front matter
        img_match = re.search(r"^image:\s*(?:\{.*?path:\s*[\"']?(.*?)[\"']?.*?\}|[\"']?(.*?)[\"']?)\s*$", fm_text, re.M)
        custom_img = None
        if img_match:
            val = (img_match.group(1) or img_match.group(2) or "").strip()
            # If val is already an OG card we generated, ignore it so we search for actual content image
            if val and not val.startswith("http") and "/assets/img/og/" not in val:
                custom_img = val

        # Description
        desc_match = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", fm_text, re.M)
        desc = desc_match.group(1).strip("\"'") if desc_match else ""

    # If no custom image in front matter, search inline markdown images
    if not custom_img:
        inline_imgs = re.findall(r"!\[.*?\]\((/assets/img/[^)\s]+|\.\./assets/img/[^)\s]+|assets/img/[^)\s]+)\)", body)
        if inline_imgs:
            first_img = inline_imgs[0].replace("../assets/", "/assets/").replace("assets/", "/assets/")
            if not first_img.endswith(".svg") and "avatar" not in first_img and "favicons" not in first_img and "/assets/img/og/" not in first_img:
                custom_img = first_img

    # If no description, generate clean excerpt from body
    if not desc:
        clean = clean_markdown_to_plain_text(body)
        if clean:
            # Never slice in the middle of a word
            if len(clean) > 220:
                truncated = clean[:220]
                if " " in truncated:
                    desc = truncated.rsplit(" ", 1)[0].rstrip("،.,;-_ ") + "..."
                else:
                    desc = truncated + "..."
            else:
                desc = clean
    else:
        desc = clean_markdown_to_plain_text(desc)

    # Determine post slug (used by Jekyll permalink)
    date_slug_match = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", file_path.stem)
    slug = date_slug_match.group(1) if date_slug_match else file_path.stem

    return {
        "slug": slug,
        "title": title,
        "category": category,
        "image": custom_img,
        "description": desc,
        "file_path": file_path,
        "is_persian": is_persian(title + " " + desc),
    }


def wrap_text(text: str, max_chars_per_line: int, max_lines: int = 3):
    """Smartly wrap text into lines without breaking words."""
    words = text.split()
    lines = []
    current_line = []
    current_len = 0

    for word in words:
        word_len = len(word)
        if current_line and (current_len + 1 + word_len) > max_chars_per_line:
            lines.append(" ".join(current_line))
            if len(lines) == max_lines:
                current_line = []
                break
            current_line = [word]
            current_len = word_len
        else:
            current_line.append(word)
            current_len += (1 + word_len) if current_line else word_len

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))

    # If truncated, add ellipsis cleanly
    joined = " ".join(words)
    wrapped_joined = " ".join(lines)
    if len(wrapped_joined) < len(joined) and lines:
        lines[-1] = lines[-1].rstrip("،.,;…-_ ") + "..."

    return lines


def generate_svg_card(post_data: dict) -> str:
    """Generate high-resolution SVG string for 1200x630 card."""
    is_fa = post_data["is_persian"]
    category = post_data["category"]
    image_rel_path = post_data["image"]

    # Modern, crisp typography stack matching transcf.org
    if is_fa:
        cat_labels = {
            "general": "یادداشت",
            "politics": "سیاست",
            "tech": "فناوری",
            "governance": "حکمرانی",
            "manifesto": "مانیفست",
        }
        cat_text = cat_labels.get(category.lower(), category)
        author_name = "آرمان ترک‌زبان"
        domain = "armantorkzaban.github.io"
        font_display = "Noto Naskh Arabic, Georgia, serif"
        font_body = "Noto Sans Arabic, Arial, sans-serif"
    else:
        cat_text = category.upper()
        author_name = "Arman Torkzaban"
        domain = "armantorkzaban.github.io"
        font_display = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
        font_body = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

    cat_text = html.escape(cat_text)
    author_name = html.escape(author_name)

    # Check if image exists
    img_b64 = None
    if image_rel_path:
        clean_img_path = image_rel_path.lstrip("/")
        full_img_path = REPO_ROOT / clean_img_path
        if full_img_path.exists():
            with open(full_img_path, "rb") as f:
                img_data = f.read()
                mime = "image/png" if full_img_path.suffix.lower() == ".png" else "image/jpeg"
                img_b64 = f"data:{mime};base64," + base64.b64encode(img_data).decode("utf-8")

    has_cover = img_b64 is not None

    if has_cover:
        # 2-column layout: Cover image + Content side
        title_lines = wrap_text(post_data["title"], max_chars_per_line=24, max_lines=3)
        max_desc_lines = 3 if len(title_lines) <= 2 else 2
        desc_lines = wrap_text(post_data["description"], max_chars_per_line=44, max_lines=max_desc_lines)

        if is_fa:
            # RTL: Cover on LEFT (x=75, y=85, 460x460), Text on RIGHT (x=580 to 1120)
            cover_x = 75
            cover_y = 85
            text_anchor_x = 1110
            avatar_cx = 1080
            avatar_cy = 525
            author_text_x = 1035
            badge_x = 1000
            badge_text_x = 1055
            divider_x1, divider_x2 = 600, 1110

            svg_title_elements = []
            y_start = 215 if len(title_lines) == 2 else (180 if len(title_lines) == 3 else 240)
            line_height = 58 if len(title_lines) > 2 else 66
            font_size = 44 if len(title_lines) > 2 else 48
            for i, line in enumerate(title_lines):
                svg_title_elements.append(
                    f'<text x="{text_anchor_x}" y="{y_start + i * line_height}" fill="#ffffff" '
                    f'font-family="{font_display}" font-size="{font_size}" font-weight="700" '
                    f'direction="rtl" text-anchor="start">{html.escape(line)}</text>'
                )

            svg_desc_elements = []
            desc_y = y_start + len(title_lines) * line_height + 25
            for i, line in enumerate(desc_lines):
                svg_desc_elements.append(
                    f'<text x="{text_anchor_x}" y="{desc_y + i * 36}" fill="#c8c8d0" '
                    f'font-family="{font_body}" font-size="22" font-weight="400" direction="rtl" text-anchor="start">{html.escape(line)}</text>'
                )

            content_svg = f"""
  <!-- Cover Image (Left) -->
  <g filter="url(#card-shadow)">
    <rect x="{cover_x - 2}" y="{cover_y - 2}" width="464" height="464" rx="26" fill="none" stroke="#ffffff" stroke-opacity="0.12" stroke-width="2"/>
    <image href="{img_b64}" x="{cover_x}" y="{cover_y}" width="460" height="460" preserveAspectRatio="xMidYMid slice" clip-path="url(#cover-clip)"/>
  </g>

  <!-- Category Badge (Right) -->
  <g>
    <rect x="{badge_x}" y="85" width="115" height="36" rx="18" fill="#007aff" fill-opacity="0.18" stroke="#2997ff" stroke-opacity="0.4" stroke-width="1"/>
    <text x="{badge_text_x}" y="109" fill="#64d2ff" font-family="{font_body}" font-size="16" font-weight="600" text-anchor="middle">{cat_text}</text>
  </g>

  <!-- Title & Description -->
  {"".join(svg_title_elements)}
  {"".join(svg_desc_elements)}

  <!-- Divider -->
  <line x1="{divider_x1}" y1="455" x2="{divider_x2}" y2="455" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1"/>

  <!-- Author Section -->
  <g>
    <image href="data:image/png;base64,{AVATAR_B64}" x="{avatar_cx - 28}" y="{avatar_cy - 28}" width="56" height="56" clip-path="url(#avatar-clip)"/>
    <circle cx="{avatar_cx}" cy="{avatar_cy}" r="29" fill="none" stroke="#2997ff" stroke-opacity="0.5" stroke-width="2"/>
    <text x="{author_text_x}" y="{avatar_cy - 7}" fill="#ffffff" font-family="{font_display}" font-size="22" font-weight="700" direction="rtl" text-anchor="start">{author_name}</text>
    <text x="{author_text_x}" y="{avatar_cy + 19}" fill="#8a8a92" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" text-anchor="end">{domain}</text>
  </g>
"""
        else:
            # LTR: Text on LEFT (x=80 to 620), Cover on RIGHT (x=665, y=85, 460x460)
            cover_x = 665
            cover_y = 85
            text_anchor_x = 80
            avatar_cx = 108
            avatar_cy = 525
            author_text_x = 150
            badge_x = 80
            badge_text_x = 135
            divider_x1, divider_x2 = 80, 620

            svg_title_elements = []
            y_start = 215 if len(title_lines) == 2 else (180 if len(title_lines) == 3 else 240)
            line_height = 58 if len(title_lines) > 2 else 66
            font_size = 44 if len(title_lines) > 2 else 48
            for i, line in enumerate(title_lines):
                svg_title_elements.append(
                    f'<text x="{text_anchor_x}" y="{y_start + i * line_height}" fill="#ffffff" '
                    f'font-family="{font_display}" font-size="{font_size}" font-weight="800" '
                    f'text-anchor="start">{html.escape(line)}</text>'
                )

            svg_desc_elements = []
            desc_y = y_start + len(title_lines) * line_height + 25
            for i, line in enumerate(desc_lines):
                svg_desc_elements.append(
                    f'<text x="{text_anchor_x}" y="{desc_y + i * 36}" fill="#c8c8d0" '
                    f'font-family="{font_body}" font-size="21" text-anchor="start">{html.escape(line)}</text>'
                )

            content_svg = f"""
  <!-- Cover Image (Right) -->
  <g filter="url(#card-shadow)">
    <rect x="{cover_x - 2}" y="{cover_y - 2}" width="464" height="464" rx="26" fill="none" stroke="#ffffff" stroke-opacity="0.12" stroke-width="2"/>
    <image href="{img_b64}" x="{cover_x}" y="{cover_y}" width="460" height="460" preserveAspectRatio="xMidYMid slice" clip-path="url(#cover-clip)"/>
  </g>

  <!-- Category Badge (Left) -->
  <g>
    <rect x="{badge_x}" y="85" width="125" height="36" rx="18" fill="#007aff" fill-opacity="0.18" stroke="#2997ff" stroke-opacity="0.4" stroke-width="1"/>
    <text x="{badge_text_x}" y="109" fill="#64d2ff" font-family="{font_body}" font-size="15" font-weight="bold" text-anchor="middle">{cat_text}</text>
  </g>

  <!-- Title & Description -->
  {"".join(svg_title_elements)}
  {"".join(svg_desc_elements)}

  <!-- Divider -->
  <line x1="{divider_x1}" y1="455" x2="{divider_x2}" y2="455" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1"/>

  <!-- Author Section -->
  <g>
    <image href="data:image/png;base64,{AVATAR_B64}" x="{avatar_cx - 28}" y="{avatar_cy - 28}" width="56" height="56" clip-path="url(#avatar-clip)"/>
    <circle cx="{avatar_cx}" cy="{avatar_cy}" r="29" fill="none" stroke="#2997ff" stroke-opacity="0.5" stroke-width="2"/>
    <text x="{author_text_x}" y="{avatar_cy - 7}" fill="#ffffff" font-family="{font_display}" font-size="22" font-weight="bold" text-anchor="start">{author_name}</text>
    <text x="{author_text_x}" y="{avatar_cy + 19}" fill="#8a8a92" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" text-anchor="start">{domain}</text>
  </g>
"""
    else:
        # Full width editorial typography layout (no cover image)
        title_lines = wrap_text(post_data["title"], max_chars_per_line=36, max_lines=2)
        desc_lines = wrap_text(post_data["description"], max_chars_per_line=60, max_lines=3)

        if is_fa:
            text_anchor_x = 1120
            avatar_cx = 1090
            avatar_cy = 525
            author_text_x = 1045
            badge_x = 1000
            badge_text_x = 1060

            svg_title_elements = []
            y_start = 215 if len(title_lines) == 2 else 240
            line_height = 70
            font_size = 54 if len(title_lines) == 2 else 58
            for i, line in enumerate(title_lines):
                svg_title_elements.append(
                    f'<text x="{text_anchor_x}" y="{y_start + i * line_height}" fill="#ffffff" '
                    f'font-family="{font_display}" font-size="{font_size}" font-weight="700" '
                    f'direction="rtl" text-anchor="start">{html.escape(line)}</text>'
                )

            svg_desc_elements = []
            desc_y = y_start + len(title_lines) * line_height + 25
            for i, line in enumerate(desc_lines):
                svg_desc_elements.append(
                    f'<text x="{text_anchor_x}" y="{desc_y + i * 38}" fill="#c8c8d0" '
                    f'font-family="{font_body}" font-size="23" font-weight="400" direction="rtl" text-anchor="start">{html.escape(line)}</text>'
                )

            content_svg = f"""
  <!-- Category Badge -->
  <g>
    <rect x="{badge_x}" y="80" width="120" height="38" rx="19" fill="#007aff" fill-opacity="0.18" stroke="#2997ff" stroke-opacity="0.4" stroke-width="1"/>
    <text x="{badge_text_x}" y="105" fill="#64d2ff" font-family="{font_body}" font-size="17" font-weight="600" text-anchor="middle">{cat_text}</text>
  </g>

  <!-- Title & Description -->
  {"".join(svg_title_elements)}
  {"".join(svg_desc_elements)}

  <!-- Subtle Quote Motif in Background -->
  <path d="M120 400 C120 320, 180 280, 240 280 C280 280, 310 310, 310 350 C310 390, 280 420, 240 420 C220 420, 205 410, 195 400 C195 440, 230 470, 270 480 L255 510 C180 490, 120 450, 120 400 Z" fill="#ffffff" opacity="0.025"/>

  <!-- Divider -->
  <line x1="80" y1="455" x2="1120" y2="455" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1"/>

  <!-- Author Section -->
  <g>
    <image href="data:image/png;base64,{AVATAR_B64}" x="{avatar_cx - 28}" y="{avatar_cy - 28}" width="56" height="56" clip-path="url(#avatar-clip)"/>
    <circle cx="{avatar_cx}" cy="{avatar_cy}" r="29" fill="none" stroke="#2997ff" stroke-opacity="0.5" stroke-width="2"/>
    <text x="{author_text_x}" y="{avatar_cy - 7}" fill="#ffffff" font-family="{font_display}" font-size="22" font-weight="700" direction="rtl" text-anchor="start">{author_name}</text>
    <text x="{author_text_x}" y="{avatar_cy + 19}" fill="#8a8a92" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" text-anchor="end">{domain}</text>
  </g>
"""
        else:
            text_anchor_x = 80
            avatar_cx = 108
            avatar_cy = 525
            author_text_x = 150
            badge_x = 80
            badge_text_x = 145

            svg_title_elements = []
            y_start = 215 if len(title_lines) == 2 else 240
            line_height = 68
            font_size = 54 if len(title_lines) == 2 else 58
            for i, line in enumerate(title_lines):
                svg_title_elements.append(
                    f'<text x="{text_anchor_x}" y="{y_start + i * line_height}" fill="#ffffff" '
                    f'font-family="{font_display}" font-size="{font_size}" font-weight="800" '
                    f'text-anchor="start">{html.escape(line)}</text>'
                )

            svg_desc_elements = []
            desc_y = y_start + len(title_lines) * line_height + 25
            for i, line in enumerate(desc_lines):
                svg_desc_elements.append(
                    f'<text x="{text_anchor_x}" y="{desc_y + i * 36}" fill="#c8c8d0" '
                    f'font-family="{font_body}" font-size="23" text-anchor="start">{html.escape(line)}</text>'
                )

            content_svg = f"""
  <!-- Category Badge -->
  <g>
    <rect x="{badge_x}" y="80" width="130" height="38" rx="19" fill="#007aff" fill-opacity="0.18" stroke="#2997ff" stroke-opacity="0.4" stroke-width="1"/>
    <text x="{badge_text_x}" y="105" fill="#64d2ff" font-family="{font_body}" font-size="16" font-weight="bold" text-anchor="middle">{cat_text}</text>
  </g>

  <!-- Title & Description -->
  {"".join(svg_title_elements)}
  {"".join(svg_desc_elements)}

  <!-- Divider -->
  <line x1="80" y1="455" x2="1120" y2="455" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1"/>

  <!-- Author Section -->
  <g>
    <image href="data:image/png;base64,{AVATAR_B64}" x="{avatar_cx - 28}" y="{avatar_cy - 28}" width="56" height="56" clip-path="url(#avatar-clip)"/>
    <circle cx="{avatar_cx}" cy="{avatar_cy}" r="29" fill="none" stroke="#2997ff" stroke-opacity="0.5" stroke-width="2"/>
    <text x="{author_text_x}" y="{avatar_cy - 7}" fill="#ffffff" font-family="{font_display}" font-size="22" font-weight="bold" text-anchor="start">{author_name}</text>
    <text x="{author_text_x}" y="{avatar_cy + 19}" fill="#8a8a92" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" text-anchor="start">{domain}</text>
  </g>
"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1c1d22"/>
      <stop offset="100%" stop-color="#0d0e11"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#2997ff"/>
      <stop offset="100%" stop-color="#007aff"/>
    </linearGradient>
    <filter id="card-shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#000000" flood-opacity="0.7"/>
    </filter>
    <clipPath id="cover-clip">
      <rect x="{75 if is_fa else 665}" y="85" width="460" height="460" rx="24"/>
    </clipPath>
    <clipPath id="avatar-clip">
      <circle cx="{avatar_cx}" cy="{avatar_cy}" r="28"/>
    </clipPath>
  </defs>

  <!-- Background -->
  <rect width="1200" height="630" fill="url(#bg)"/>

  <!-- Subtle glow circles -->
  <circle cx="{1100 if is_fa else 100}" cy="100" r="300" fill="#007aff" opacity="0.06"/>
  <circle cx="{150 if is_fa else 1050}" cy="550" r="280" fill="#2997ff" opacity="0.04"/>

  <!-- Top Accent Bar -->
  <rect x="0" y="0" width="1200" height="5" fill="url(#accent)"/>

  <!-- Outer frame border -->
  <rect x="25" y="25" width="1150" height="580" rx="24" fill="none" stroke="#ffffff" stroke-opacity="0.08" stroke-width="1.5"/>

  {content_svg}
</svg>"""


def render_svg_to_png(svg_str: str, out_png_path: Path):
    """Render an SVG string to a 1200x630 PNG using rsvg-convert or ImageMagick."""
    tmp_svg = out_png_path.with_suffix(".tmp.svg")
    tmp_svg.write_text(svg_str, encoding="utf-8")

    # Ensure fontconfig configuration exists pointing to local fonts
    fonts_conf = FONTS_DIR / "fonts.conf"
    if not fonts_conf.exists() or str(FONTS_DIR) not in fonts_conf.read_text(encoding="utf-8"):
        fonts_conf.write_text(f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>{FONTS_DIR}</dir>
  <include ignore_missing="yes">/opt/homebrew/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
</fontconfig>""", encoding="utf-8")

    env = os.environ.copy()
    env["FONTCONFIG_FILE"] = str(fonts_conf)

    try:
        res = subprocess.run(
            ["rsvg-convert", "-w", "1200", "-h", "630", str(tmp_svg), "-o", str(out_png_path)],
            capture_output=True,
            text=True,
            env=env
        )
        if res.returncode == 0:
            return True

        for cmd in ["magick", "convert"]:
            res2 = subprocess.run(
                [cmd, str(tmp_svg), "-resize", "1200x630", str(out_png_path)],
                capture_output=True,
                text=True,
                env=env
            )
            if res2.returncode == 0:
                return True

        print(f"Error rendering {out_png_path}: {res.stderr or res2.stderr}", file=sys.stderr)
        return False
    finally:
        if tmp_svg.exists():
            tmp_svg.unlink()


def generate_default_card(force: bool = False):
    """Generate the site-wide default social preview card."""
    out_png = OG_DIR / "default-preview.png"
    if out_png.exists() and not force:
        return

    data = {
        "slug": "default-preview",
        "title": "Arman Torkzaban",
        "category": "BLOG",
        "image": None,
        "description": "Thoughts on digital democracy, ZK governance, and the Iranian democratic transition.",
        "file_path": Path("default"),
        "is_persian": False,
    }
    svg = generate_svg_card(data)
    render_svg_to_png(svg, out_png)
    print(f"✓ Generated default preview: {out_png.name}")


def main():
    force = "--force" in sys.argv
    single_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--post" and i + 1 < len(sys.argv):
            single_file = Path(sys.argv[i + 1])

    # Default site card
    generate_default_card(force=force)

    # Posts
    if single_file:
        posts = [single_file]
    else:
        posts = sorted(list(POSTS_DIR.glob("*.md")))

    count = 0
    for post_file in posts:
        post_data = parse_post(post_file)
        out_png = OG_DIR / f"{post_data['slug']}.png"

        # Check if rebuild needed
        if not force and out_png.exists():
            if out_png.stat().st_mtime >= post_file.stat().st_mtime:
                continue

        svg = generate_svg_card(post_data)
        ok = render_svg_to_png(svg, out_png)
        if ok:
            count += 1
            print(f"✓ Generated [{post_data['slug']}]: {out_png.name}")

    print(f"Finished: {count} OG image(s) created/updated.")


if __name__ == "__main__":
    main()
