"""
AI-powered SEO generator using Claude API.
Generates title, description, and tags for YouTube Shorts.
"""
import os
import re
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


async def generate_seo(filename: str, topic: str = "") -> dict:
    context = f"Filename: {filename}"
    if topic:
        context += f"\nVideo topic/context: {topic}"

    prompt = f"""You are a YouTube SEO expert specializing in Shorts and viral content.

Given this clip:
{context}

Generate optimized YouTube metadata. Respond ONLY with valid JSON, no markdown, no explanation:
{{
  "title": "Engaging title under 100 chars with relevant keywords",
  "description": "2-3 paragraph description with keywords, hooks, and a CTA. Include relevant hashtags at the end.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "hashtags": ["#Shorts", "#relevant", "#hashtags"]
}}

Rules:
- Title must be click-worthy and keyword-rich
- Description should start with a strong hook
- Include 10 relevant tags (mix of broad and niche)
- Tags should be single words or short phrases
- Always include #Shorts in hashtags"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)
