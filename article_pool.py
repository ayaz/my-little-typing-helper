from __future__ import annotations
from collections import deque
from threading import Lock
from wikipedia import Article


class ArticlePool:
    """Thread-safe pool of pre-fetched Wikipedia articles with duplicate prevention."""

    def __init__(self, target_size: int = 3, min_size: int = 1, history_size: int = 10):
        self._pool: deque[Article] = deque(maxlen=target_size)
        self._recently_used: deque[str] = deque(maxlen=history_size)  # Track last N article URLs
        self._lock = Lock()
        self._target_size = target_size
        self._min_size = min_size
        self._fetch_failures = 0

    def get_article(self) -> Article | None:
        """Get an article from pool and mark as used (non-blocking)."""
        with self._lock:
            if self._pool:
                article = self._pool.popleft()
                self._recently_used.append(article.url)  # Track usage
                return article
            return None

    def is_duplicate(self, article: Article) -> bool:
        """Check if article was recently used."""
        with self._lock:
            return article.url in self._recently_used

    def add_article(self, article: Article) -> None:
        """Add article to pool if not a duplicate (thread-safe)."""
        with self._lock:
            if article.url not in self._recently_used:
                self._pool.append(article)
                self._fetch_failures = 0

    def is_full(self) -> bool:
        """Check if pool is at capacity."""
        with self._lock:
            return len(self._pool) >= self._target_size

    def record_fetch_failure(self) -> None:
        """Track fetch failures for backoff logic."""
        with self._lock:
            self._fetch_failures += 1
