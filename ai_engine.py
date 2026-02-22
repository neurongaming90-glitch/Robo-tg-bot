import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-a0a001c9f6304ceb9c0ae667ead7270d")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "AIzaSyAwX-T75vih-VIHMA_fH1Dx9RraKfLHsqM")

# ── Endpoints ─────────────────────────────────────────────────────────────────
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

DEEPSEEK_MODEL = "deepseek-chat"

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
    "funny": "😂 DeepSeek aur Gemini dono so gaye! Thodi der baad try karo 😴",
    "savage": "🔥 Both AIs gave up on you. Impressive. Try again later.",
}


def _build_messages(query: str, mode: str, wiki_context: str = None):
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])
    user_message = query
    if wiki_context:
        user_message = (
            f"Question: {query}\n\n"
            f"Wikipedia context:\n{wiki_context}\n\n"
            f"Use this context if relevant to enhance your answer."
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


async def _call_deepseek(messages: list, mode: str) -> str | None:
    """Try DeepSeek API."""
    if not DEEPSEEK_API_KEY:
        return None
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(DEEPSEEK_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"DeepSeek failed [{resp.status_code}]: {resp.text[:200]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ DeepSeek OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"DeepSeek exception: {type(e).__name__}: {e}")
        return None


async def _call_gemini(messages: list, mode: str) -> str | None:
    """Try Gemini API as fallback."""
    if not GEMINI_API_KEY:
        logger.warning("Gemini key not set — skipping")
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


async def get_ai_response(query: str, mode: str = "smart", wiki_context: str = None) -> str:
    """
    Dual fallback:
    1️⃣ DeepSeek → 2️⃣ Gemini → Static message
    """
    messages = _build_messages(query, mode, wiki_context)

    # 1️⃣ DeepSeek
    response = await _call_deepseek(messages, mode)
    if response:
        return response

    # 2️⃣ Gemini fallback
    logger.info("DeepSeek failed → trying Gemini...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ Both failed
    logger.error("Both DeepSeek and Gemini failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
