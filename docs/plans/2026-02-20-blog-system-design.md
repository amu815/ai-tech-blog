# AI Tech Lab - Blog System Design

## Overview
AI/Tech/Research blog with automated article generation using local LLM (Ollama + Qwen3:32b on DGX Spark).

## Stack
- **SSG**: Hugo + PaperMod theme
- **Article Generation**: Python CLI → Ollama API → Markdown
- **Hosting**: Cloudflare Pages (free, CDN)
- **Languages**: Japanese + English (Hugo multilingual)
- **Categories**: AI, Technology, Research
- **Monetization**: Google AdSense

## Architecture
```
keywords → generate.py → Ollama API → content/*.md → git push → Cloudflare Pages
```

## Article Generation CLI
- `python tools/generate.py --keyword "..." --lang ja --category ai`
- `python tools/generate.py --batch tools/keywords.txt`
- Generates SEO-optimized front matter + body

## Deployment
1. Push to GitHub
2. Cloudflare Pages auto-builds from `main` branch
3. Build command: `hugo --gc --minify`
4. Output dir: `public`
