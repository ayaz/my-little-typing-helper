from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any


STATS_DIR = Path.home() / ".typing-tutor"
STATS_FILE = STATS_DIR / "stats.json"


@dataclass
class SessionRecord:
    id: str
    started_at: str
    ended_at: str
    duration_s: float
    source: str
    source_meta: dict
    text_len: int
    typed_len: int
    correct_chars: int
    wpm: float
    accuracy: float


class StatsStore:
    def __init__(self, path: Path = STATS_FILE) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"sessions": []}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return {"sessions": []}

    def append_session(self, record: SessionRecord) -> None:
        data = self.load()
        data.setdefault("sessions", [])
        data["sessions"].append(asdict(record))
        self._save(data)

    def _save(self, data: dict[str, Any]) -> None:
        STATS_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))
