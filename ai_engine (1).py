import os
import httpx
import logging

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-51fb497ebdb9419b95db3eab9e61fb49")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"  # Correct URL (no /v1/)
MODEL = "deepseek-chat"

SYSTEM_PROMPTS = {
    "smart": (
        "You are a highly intelligent AI assistant. Provide accurate, detailed, "
        "and well-structured responses. Use facts, examples, and clear explanations. "
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
        "Don't sugarcoat anything. Still answer the question, but with brutal honesty and attitude. "
        "Always respond in the same language the user asked in."
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 My AI brain is taking a quick nap. Please try again in a moment!",
    "funny": "😂 Even I have bad days! My circuits are confused right now. Try again?",
    "savage": "🔥 Even savage beasts need rest. API is down. Deal with it and try later.",
}


async def get_ai_response(query: str, mode: str = "smart", wiki_context: str = None) -> str:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])

    user_message = query
    if wiki_context:
        user_message = (
            f"Question: {query}\n\n"
            f"Additional context from Wikipedia:\n{wiki_context}\n\n"
            f"Please use this context to enhance your response if relevant."
        )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"DeepSeek error {response.status_code}: {response.text}")
                return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.info(f"DeepSeek OK, response length: {len(content)}")
            return content

    except httpx.TimeoutException:
        logger.error("DeepSeek API timeout after 30s")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except httpx.RequestError as e:
        logger.error(f"DeepSeek request error: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except (KeyError, IndexError) as e:
        logger.error(f"DeepSeek parse error: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except Exception as e:
        logger.error(f"Unexpected AI error: {type(e).__name__}: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
