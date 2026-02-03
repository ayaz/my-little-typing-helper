from __future__ import annotations

from dataclasses import dataclass
import re
import requests


WIKI_RANDOM_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/random/summary"


@dataclass
class Article:
    title: str
    url: str
    text: str
    extract_len: int


def _clean_text(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def fetch_random_article(min_chars: int = 600, max_chars: int = 1200, tries: int = 5) -> Article:
    last_article = None
    for _ in range(tries):
        response = requests.get(
            WIKI_RANDOM_SUMMARY_URL,
            timeout=8,
            allow_redirects=True,
            headers={
                "User-Agent": "my-typing-tutor/0.1 (macOS; python requests)",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        extract = data.get("extract") or ""
        text = _clean_text(extract)
        title = data.get("title") or "Unknown Title"
        url = (
            data.get("content_urls", {})
            .get("desktop", {})
            .get("page", "https://en.wikipedia.org")
        )

        if not text:
            continue
        if not _is_ascii(text):
            continue

        if len(text) > max_chars:
            text = text[:max_chars]

        last_article = Article(title=title, url=url, text=text, extract_len=len(text))

        if len(text) >= min_chars:
            return last_article

    if last_article is None:
        return Article(
            title="Wikipedia",
            url="https://en.wikipedia.org",
            text="Unable to load content. Please try again.",
            extract_len=0,
        )

    return last_article
