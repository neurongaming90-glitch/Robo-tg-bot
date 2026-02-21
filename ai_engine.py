import os
from typing import Optional

import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

MODE_INSTRUCTIONS = {
    "smart": "You are precise, insightful, and professional. Keep responses useful and clear.",
    "funny": "You are witty and humorous while still being accurate and helpful.",
    "savage": "You are bold and savage but avoid abuse, hate, or harmful content. Keep it clever.",
}


async def generate_ai_response(prompt: str, mode: str = "smart", wiki_context: Optional[str] = None) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "⚠️ AI service is not configured. Please set DEEPSEEK_API_KEY."

    style_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["smart"])

    context_block = f"\nWikipedia context:\n{wiki_context}\n" if wiki_context else ""
    user_prompt = (
        f"User question: {prompt}{context_block}\n"
        "Answer in a compact but helpful format suitable for Telegram chats."
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": style_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        if content:
            return content
    except Exception:
        pass

    return "🤖 I couldn't reach the AI service right now. Please try again shortly."
