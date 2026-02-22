import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "164b1667-9a55-4eaa-aa39-7f63f252da52")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "AIzaSyAwX-T75vih-VIHMA_fH1Dx9RraKfLHsqM")

# ── Endpoints ─────────────────────────────────────────────────────────────────
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

SAMBANOVA_MODEL = "Meta-Llama-3.3-70B-Instruct"

# ── Personality Prompts ───────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "smart": (
        "You are a highly intelligent AI assistant. Provide accurate, detailed, "
        "and well-structured responses. Use facts and clear explanations. "
        "Be professional yet approachable. Keep responses concise but comprehensive. "
        "Always respond in the same language the user asked in."
    ),
    "funny": (
        "You are a witty, humorous AI assistant. Answer questions with jokes, puns, "
        "funny analogies, and a light-hearted tone. Keep it entertaining while still "
        "being helpful. Add relevant emojis and make the user laugh! "
        "Always respond in the same language the user asked in."
    ),
    "savage": (
        "You are a brutally honest, savage AI assistant. Cut through the BS and give "
        "raw, unfiltered truth. Be bold, direct, and unapologetically honest. "
        "Don't sugarcoat anything. Still answer the question, but with brutal honesty. "
        "Always respond in the same language the user asked in."
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 Both AI engines are resting right now. Please try again in a moment!",
    "funny": "😂 SambaNova aur Gemini dono so gaye ek saath! Thodi der baad try karo 😴",
    "savage": "🔥 Both AIs gave up on you. Impressive. Try again later.",
}


def _build_messages(query: str, mode: str, wiki_context: str = None, news_context: str = None) -> list:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])
    user_message = query

    extra = []
    if wiki_context:
        extra.append(f"Wikipedia context:\n{wiki_context}")
    if news_context:
        extra.append(f"Latest News:\n{news_context}")

    if extra:
        user_message = f"Question: {query}\n\n" + "\n\n".join(extra) + "\n\nUse this context if relevant."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


async def _call_sambanova(messages: list, mode: str) -> str | None:
    """Try SambaNova API — Llama 3.3 70B."""
    if not SAMBANOVA_API_KEY:
        return None
    payload = {
        "model": SAMBANOVA_MODEL,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(SAMBANOVA_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"SambaNova failed [{resp.status_code}]: {resp.text[:200]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ SambaNova OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"SambaNova exception: {type(e).__name__}: {e}")
        return None


async def _call_gemini(messages: list, mode: str) -> str | None:
    """Try Gemini API as fallback."""
    if not GEMINI_API_KEY:
        return None

    system_prompt = messages[0]["content"]
    user_text = messages[1]["content"]
    combined = f"{system_prompt}\n\nUser: {user_text}"

    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": 500,
            "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
        },
    }
    try:
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Gemini failed [{resp.status_code}]: {resp.text[:200]}")
                return None
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"✅ Gemini OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Gemini exception: {type(e).__name__}: {e}")
        return None


async def get_ai_response(
    query: str,
    mode: str = "smart",
    wiki_context: str = None,
    news_context: str = None,
) -> str:
    """
    Dual fallback:
    1️⃣ SambaNova (Llama 3.3 70B) → 2️⃣ Gemini → Static message
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    # 1️⃣ SambaNova
    response = await _call_sambanova(messages, mode)
    if response:
        return response

    # 2️⃣ Gemini fallback
    logger.info("SambaNova failed → trying Gemini...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ Both failed
    logger.error("Both SambaNova and Gemini failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
