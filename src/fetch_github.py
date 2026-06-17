"""Fetch trending AI projects from GitHub Search API."""

import logging
import os
import time
from datetime import datetime, timezone

import requests
import yaml

from src.dedupe import dedupe_by_url

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sources.yaml")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
API_URL = "https://api.github.com/search/repositories"
PER_KEYWORD = 10
MIN_STARS = 10


def load_keywords() -> list[str]:
    """Load search keywords from YAML config."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("keywords", [])


def _search(keyword: str) -> list[dict]:
    """Search GitHub for a single keyword, returning parsed items."""
    since = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")  # This month
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Panda-XHS-Weekly/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    params = {
        "q": f"{keyword} pushed:>={since}",
        "sort": "stars",
        "order": "desc",
        "per_page": PER_KEYWORD,
    }

    try:
        resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
        if resp.status_code == 403:
            logger.warning("GitHub rate limited for keyword '%s'", keyword)
            return []
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        logger.info("Keyword '%s': %d results", keyword, len(items))
        return [
            {
                "url": item.get("html_url", ""),
                "name": item.get("full_name", ""),
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language") or "N/A",
                "description": (item.get("description") or "").strip(),
                "keyword": keyword,
            }
            for item in items
            if item.get("stargazers_count", 0) >= MIN_STARS
        ]
    except Exception as e:
        logger.warning("GitHub search '%s' failed: %s", keyword, e)
        return []


def fetch_github_projects() -> list[dict]:
    """Fetch all keywords, deduplicate, return top 10 by stars."""
    keywords = load_keywords()
    logger.info("Fetching GitHub: %d keywords", len(keywords))

    all_items: list[dict] = []
    for kw in keywords:
        items = _search(kw)
        all_items.extend(items)
        if kw != keywords[-1]:
            time.sleep(1.5)  # Rate limit: avoid secondary rate limits

    unique = dedupe_by_url(all_items)
    unique.sort(key=lambda x: x["stars"], reverse=True)
    top = unique[:10]
    logger.info("GitHub fetch done: %d raw, %d unique, %d top", len(all_items), len(unique), len(top))
    return top


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    projects = fetch_github_projects()
    for i, p in enumerate(projects):
        print(f"  [{i+1}] {p['name']} ⭐{p['stars']} ({p['keyword']})")
