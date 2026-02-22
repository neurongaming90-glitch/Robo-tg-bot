import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY",  "sk-a0a001c9f6304ceb9c0ae667ead7270d")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY",  "c8c52216-bded-46ac-b0f0-4e0747790a14")

# ── Endpoints ─────────────────────────────────────────────
DEEPSEEK_URL  = "https://api.deepseek.com/chat/completions"
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"

DEEPSEEK_MODEL  = "deepseek-chat"
SAMBANOVA_MODEL = "Meta-Llama-3.3-70B-Instruct"  # Sambanova best free model

# ── Personality Prompts ───────────────────────────────────
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
    "funny": "😂 My two brains both crashed at once — what are the odds?! Try again!",
    "savage": "🔥 Both AIs gave up on you. Impressive. Try again later.",
}


def _build_messages(query: str, mode: str, wiki_context: str = None) -> list:
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
    """Try DeepSeek API. Returns response string or None on failure."""
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
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(DEEPSEEK_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"DeepSeek failed [{resp.status_code}]: {resp.text[:200]}")
                return None
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ DeepSeek responded ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"DeepSeek exception: {type(e).__name__}: {e}")
        return None


async def _call_sambanova(messages: list, mode: str) -> str | None:
    """Try Sambanova API as fallback. Returns response string or None on failure."""
    if not SAMBANOVA_API_KEY:
        logger.warning("Sambanova API key not set — skipping fallback")
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
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(SAMBANOVA_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Sambanova failed [{resp.status_code}]: {resp.text[:200]}")
                return None
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ Sambanova responded ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Sambanova exception: {type(e).__name__}: {e}")
        return None


async def get_ai_response(query: str, mode: str = "smart", wiki_context: str = None) -> str:
    """
    Main function:
    1st → DeepSeek
    2nd → Sambanova (Llama 70B) as fallback
    3rd → Static fallback message
    """
    messages = _build_messages(query, mode, wiki_context)

    # 1️⃣ Try DeepSeek first
    response = await _call_deepseek(messages, mode)
    if response:
        return response

    # 2️⃣ Fallback to Sambanova
    logger.info("DeepSeek failed → trying Sambanova (Llama 70B)...")
    response = await _call_sambanova(messages, mode)
    if response:
        return response

    # 3️⃣ Both failed
    logger.error("Both DeepSeek and Sambanova failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
