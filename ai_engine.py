import os
import httpx
import logging

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-51fb497ebdb9419b95db3eab9e61fb49")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPTS = {
    "smart": (
        "You are a highly intelligent AI assistant. Provide accurate, detailed, "
        "and well-structured responses. Use facts, examples, and clear explanations. "
        "Be professional yet approachable. Keep responses concise but comprehensive."
    ),
    "funny": (
        "You are a witty, humorous AI assistant. Answer questions with jokes, puns, "
        "funny analogies, and a light-hearted tone. Keep it entertaining while still "
        "being helpful. Add relevant emojis and make the user laugh!"
    ),
    "savage": (
        "You are a brutally honest, savage AI assistant. Cut through the BS and give "
        "raw, unfiltered truth. Be bold, direct, and unapologetically honest. "
        "Don't sugarcoat anything. Still answer the question, but with brutal honesty and attitude."
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 My AI brain is taking a quick nap. Please try again in a moment!",
    "funny": "😂 Even I have bad days! My circuits are confused right now. Try again?",
    "savage": "🔥 Even savage beasts need rest. API's down. Deal with it and try later.",
}


async def get_ai_response(query: str, mode: str = "smart", wiki_context: str = None) -> str:
    """
    Get AI response from DeepSeek API.
    Falls back to a canned message if API fails.
    """
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
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e.response.status_code} - {e.response.text}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except httpx.RequestError as e:
        logger.error(f"DeepSeek API request error: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except (KeyError, IndexError) as e:
        logger.error(f"DeepSeek API response parse error: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
    except Exception as e:
        logger.error(f"Unexpected AI error: {e}")
        return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
