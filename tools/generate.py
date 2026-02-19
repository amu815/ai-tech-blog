#!/usr/bin/env python3
"""
AI Tech Lab - Article Generator
Generates SEO-optimized blog articles using local Ollama LLM.

Usage:
  python generate.py --keyword "ローカルLLMの始め方" --lang ja --category ai
  python generate.py --keyword "How to fine-tune LLMs" --lang en --category ai
  python generate.py --batch keywords.txt
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:32b"
BLOG_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = BLOG_ROOT / "content"

CATEGORIES = {
    "ai": {"ja": "AI / Machine Learning", "en": "AI / Machine Learning"},
    "tech": {"ja": "テクノロジー", "en": "Technology"},
    "research": {"ja": "研究", "en": "Research"},
}

PROMPT_JA = """/no_think
あなたはSEOに精通したテクニカルライターです。以下のキーワードについて、高品質なブログ記事を書いてください。

キーワード: {keyword}
カテゴリ: {category}

以下のJSON形式で出力してください。他の文言は一切不要です。JSONのみ返してください。
{{
  "title": "SEOに最適化されたタイトル（60文字以内）",
  "description": "メタディスクリプション（120文字以内）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "body": "記事本文（マークダウン形式、## 見出しを4-6個使い、各セクション200-400字、合計2000-3000字）"
}}

記事の要件:
- 読者にとって実用的で具体的な内容にする
- 専門用語には簡潔な説明を加える
- コード例やコマンド例がある場合はコードブロックで記載
- 自然な日本語で書く
- 「まとめ」セクションを最後に含める
"""

PROMPT_EN = """/no_think
You are a technical writer with SEO expertise. Write a high-quality blog article about the following keyword.

Keyword: {keyword}
Category: {category}

Output ONLY in the following JSON format. No other text.
{{
  "title": "SEO-optimized title (under 60 characters)",
  "description": "Meta description (under 160 characters)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "body": "Article body in Markdown format, use 4-6 ## headings, 150-300 words per section, 1500-2500 words total"
}}

Article requirements:
- Practical and specific content for readers
- Include brief explanations for technical terms
- Use code blocks for code/command examples where applicable
- Write in natural, engaging English
- Include a "Conclusion" section at the end
"""


def call_ollama(prompt: str) -> str:
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 4096, "temperature": 0.7},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        sys.exit(1)


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response using bracket matching."""
    # Find the first { and match brackets to find the complete JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON found in response:\n{text[:500]}")

    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            if in_string:
                escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if depth != 0:
        raise ValueError(f"Unbalanced JSON in response:\n{text[:500]}")

    json_str = text[start:end + 1]
    return json.loads(json_str)


def slugify(text: str) -> str:
    """Create URL-friendly slug from text."""
    # For Japanese, use a hash-based approach
    if re.search(r"[\u3000-\u9fff]", text):
        # Transliterate common words, fallback to keyword-based slug
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if not slug or len(slug) < 3:
            slug = f"article-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return slug[:80]
    else:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        return slug[:80]


def generate_article(keyword: str, lang: str, category: str) -> Path:
    """Generate a single article and save it as a Hugo content file."""
    if category not in CATEGORIES:
        print(f"Invalid category: {category}. Use: {', '.join(CATEGORIES.keys())}")
        sys.exit(1)

    if lang not in ("ja", "en"):
        print(f"Invalid language: {lang}. Use: ja, en")
        sys.exit(1)

    cat_name = CATEGORIES[category][lang]
    prompt_template = PROMPT_JA if lang == "ja" else PROMPT_EN
    prompt = prompt_template.format(keyword=keyword, category=cat_name)

    print(f"Generating: [{lang}] [{category}] {keyword} ...")
    response = call_ollama(prompt)

    try:
        article = extract_json(response)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse JSON: {e}", file=sys.stderr)
        print(f"Raw response:\n{response[:1000]}", file=sys.stderr)
        sys.exit(1)

    title = article.get("title", keyword)
    description = article.get("description", "")
    tags = article.get("tags", [])
    body = article.get("body", "")

    # Create front matter
    date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    slug = slugify(title)

    front_matter = f"""---
title: "{title}"
date: {date}
description: "{description}"
tags: {json.dumps(tags, ensure_ascii=False)}
categories: ["{cat_name}"]
slug: "{slug}"
ShowToc: true
TocOpen: false
draft: false
---

"""

    content = front_matter + body + "\n"

    # Save file
    filename = f"{slug}.md"
    output_dir = CONTENT_DIR / lang / category
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    output_path.write_text(content, encoding="utf-8")
    print(f"  Saved: {output_path.relative_to(BLOG_ROOT)}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate blog articles using local LLM")
    parser.add_argument("--keyword", "-k", help="Article keyword/topic")
    parser.add_argument("--lang", "-l", default="ja", choices=["ja", "en"], help="Language (default: ja)")
    parser.add_argument("--category", "-c", default="ai", choices=list(CATEGORIES.keys()), help="Category (default: ai)")
    parser.add_argument("--batch", "-b", help="Path to keywords file (one per line, format: keyword|lang|category)")
    args = parser.parse_args()

    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"Batch file not found: {batch_file}")
            sys.exit(1)

        generated = []
        for line in batch_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            keyword = parts[0].strip()
            lang = parts[1].strip() if len(parts) > 1 else "ja"
            category = parts[2].strip() if len(parts) > 2 else "ai"
            path = generate_article(keyword, lang, category)
            generated.append(path)

        print(f"\nGenerated {len(generated)} articles.")

    elif args.keyword:
        generate_article(args.keyword, args.lang, args.category)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
