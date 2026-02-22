import os
import httpx
import logging

logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "cab6a65357584381ac5a4e66fc5ff60f")  # newsapi.org key yahan ya Railway variable mein
NEWS_URL = "https://newsapi.org/v2/everything"
NEWS_TOP_URL = "https://newsapi.org/v2/top-headlines"


async def get_news(query: str, max_articles: int = 3) -> str | None:
    """
    Fetch latest news for a query using NewsAPI.
    Returns formatted string or None if unavailable.
    """
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not set — skipping news fetch")
        return None

    # Detect if it's a general news query
    news_keywords = ["news", "latest", "today", "breaking", "khabar", "aaj"]
    is_general = any(kw in query.lower() for kw in news_keywords)

    try:
        if is_general:
            # Top headlines
            params = {
                "apiKey": NEWS_API_KEY,
                "language": "en",
                "pageSize": max_articles,
                "sortBy": "publishedAt",
            }
            url = NEWS_TOP_URL
        else:
            # Search specific topic
            params = {
                "apiKey": NEWS_API_KEY,
                "q": query,
                "language": "en",
                "pageSize": max_articles,
                "sortBy": "publishedAt",
            }
            url = NEWS_URL

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"NewsAPI failed [{resp.status_code}]")
                return None

            data = resp.json()
            articles = data.get("articles", [])

            if not articles:
                return None

            # Format articles
            lines = []
            for i, article in enumerate(articles[:max_articles], 1):
                title = article.get("title", "No title")
                source = article.get("source", {}).get("name", "Unknown")
                description = article.get("description", "")
                # Clean up titles that have source appended
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                lines.append(f"{i}. *{title}* — _{source}_")
                if description:
                    lines.append(f"   {description[:100]}...")

            result = "\n".join(lines)
            logger.info(f"✅ NewsAPI OK — {len(articles)} articles")
            return result

    except Exception as e:
        logger.warning(f"NewsAPI exception: {type(e).__name__}: {e}")
        return None


def is_news_query(query: str) -> bool:
    """Check if query is asking for news."""
    keywords = [
        "news", "latest", "today", "breaking", "current", "recent",
        "khabar", "aaj ki", "taaza", "headline", "update", "happened",
        "trump", "modi", "politics", "election", "war", "match", "score"
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)
