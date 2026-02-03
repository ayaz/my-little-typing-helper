from __future__ import annotations

import datetime as dt
import uuid

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static, TextArea
from rich.markup import escape
from rich.console import Group
from rich.table import Table

from metrics import compute_metrics
from stats import SessionRecord, StatsStore
from wikipedia import fetch_random_article


class HomeScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="home"):
            yield Static("Typing Tutor", id="title")
            yield Static("Daily practice with random Wikipedia text.", id="subtitle")
            with Horizontal(id="home-buttons"):
                yield Button("Start Session", id="start", variant="success")
                yield Button("View Stats", id="stats")
                yield Button("Quit", id="quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.app.push_screen(SessionScreen())
        elif event.button.id == "stats":
            self.app.push_screen(StatsScreen())
        elif event.button.id == "quit":
            self.app.exit()


class SessionScreen(Screen):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self.target_text = ""
        self.started_at: dt.datetime | None = None
        self.article_meta: dict = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="session"):
            yield Static("Loading lesson...", id="lesson-title")
            yield Static("", id="lesson-text")
            with Horizontal(id="metrics"):
                yield Static("WPM: 0.0", id="wpm")
                yield Static("Accuracy: 0.0%", id="accuracy")
            yield TextArea("", id="typing-area")
            with Horizontal(id="session-buttons"):
                yield Button("Finish", id="finish", variant="primary")
                yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._load_lesson()

    def _load_lesson(self) -> None:
        article = fetch_random_article()
        self.article_meta = {
            "title": article.title,
            "url": article.url,
            "extract_len": article.extract_len,
        }
        self.target_text = article.text

        self.query_one("#lesson-title", Static).update(f"Lesson: {article.title}")
        self._update_lesson_text("")
        self.started_at = dt.datetime.utcnow()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if not self.started_at:
            return

        typed_text = self.query_one("#typing-area", TextArea).text
        elapsed_s = (dt.datetime.utcnow() - self.started_at).total_seconds()
        metrics = compute_metrics(self.target_text, typed_text, elapsed_s)

        wpm_value = metrics["wpm"]
        accuracy_value = metrics["accuracy"] * 100.0

        self.query_one("#wpm", Static).update(f"WPM: {wpm_value:.1f}")
        self.query_one("#accuracy", Static).update(f"Accuracy: {accuracy_value:.1f}%")
        self._update_lesson_text(typed_text)

        if len(typed_text) >= len(self.target_text):
            self._finish_session(typed_text, metrics, elapsed_s)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "finish":
            typed_text = self.query_one("#typing-area", TextArea).text
            if not self.started_at:
                self.app.pop_screen()
                return
            elapsed_s = (dt.datetime.utcnow() - self.started_at).total_seconds()
            metrics = compute_metrics(self.target_text, typed_text, elapsed_s)
            self._finish_session(typed_text, metrics, elapsed_s)

    def _finish_session(self, typed_text: str, metrics: dict, elapsed_s: float) -> None:
        record = SessionRecord(
            id=str(uuid.uuid4()),
            started_at=self.started_at.isoformat() if self.started_at else "",
            ended_at=dt.datetime.utcnow().isoformat(),
            duration_s=elapsed_s,
            source="wikipedia",
            source_meta=self.article_meta,
            text_len=len(self.target_text),
            typed_len=metrics["total_typed"],
            correct_chars=metrics["correct_chars"],
            wpm=metrics["wpm"],
            accuracy=metrics["accuracy"],
        )
        StatsStore().append_session(record)
        self.app.push_screen(SummaryScreen(record))

    def _update_lesson_text(self, typed_text: str) -> None:
        rendered = []
        for i, ch in enumerate(self.target_text):
            if i < len(typed_text):
                if typed_text[i] == ch:
                    rendered.append(f"[on #2f4f2f]{escape(ch)}[/]")
                else:
                    rendered.append(f"[on #4f2f2f]{escape(ch)}[/]")
            else:
                rendered.append(escape(ch))
        self.query_one("#lesson-text", Static).update("".join(rendered))


class SummaryScreen(Screen):
    BINDINGS = [("enter", "home", "Home"), ("escape", "home", "Home")]

    def __init__(self, record: SessionRecord) -> None:
        super().__init__()
        self.record = record

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="summary"):
            yield Static("Session Summary", id="summary-title")
            yield Static(f"WPM: {self.record.wpm:.1f}", id="summary-wpm")
            yield Static(f"Accuracy: {self.record.accuracy * 100.0:.1f}%", id="summary-accuracy")
            yield Static(f"Duration: {self.record.duration_s:.1f}s", id="summary-duration")
            yield Static(f"Article: {self.record.source_meta.get('title', 'Unknown')}")
            yield Button("Back to Home", id="home", variant="success")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "home":
            self.app.pop_screen()
            self.app.pop_screen()

    def action_home(self) -> None:
        self.app.pop_screen()
        self.app.pop_screen()


class StatsScreen(Screen):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="stats"):
            yield Static("Stats Summary", id="stats-title")
            yield Static("", id="stats-body")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        data = StatsStore().load()
        sessions = data.get("sessions", [])
        total = len(sessions)
        avg_wpm = sum(s.get("wpm", 0.0) for s in sessions) / total if total else 0.0
        avg_acc = (
            sum(s.get("accuracy", 0.0) for s in sessions) / total if total else 0.0
        )

        def _session_key(session: dict) -> str:
            return session.get("ended_at") or session.get("started_at") or ""

        sessions_sorted = sorted(sessions, key=_session_key, reverse=True)

        summary = (
            f"Total Sessions: {total}\n"
            f"Average WPM: {avg_wpm:.1f}\n"
            f"Average Accuracy: {avg_acc * 100.0:.1f}%\n"
        )

        def _humanize_timestamp(iso_ts: str) -> str:
            if not iso_ts:
                return "Unknown time"
            try:
                parsed = dt.datetime.fromisoformat(iso_ts)
            except ValueError:
                return iso_ts
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            now = dt.datetime.now(dt.timezone.utc)
            delta = now - parsed
            seconds = max(delta.total_seconds(), 0.0)

            if seconds < 60:
                return "just now"
            if seconds < 3600:
                minutes = int(seconds // 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            if seconds < 86400:
                hours = int(seconds // 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            if seconds < 86400 * 30:
                days = int(seconds // 86400)
                return f"{days} day{'s' if days != 1 else ''} ago"
            if seconds < 86400 * 365:
                months = int(seconds // (86400 * 30))
                return f"{months} month{'s' if months != 1 else ''} ago"
            years = int(seconds // (86400 * 365))
            return f"{years} year{'s' if years != 1 else ''} ago"

        table = Table(show_header=True, box=None, show_edge=False, pad_edge=False)
        table.add_column("When", width=18, no_wrap=True)
        table.add_column("WPM", justify="right", width=6, no_wrap=True)
        table.add_column("Accuracy", justify="right", width=10, no_wrap=True)
        table.add_column("Error", justify="right", width=8, no_wrap=True)

        for session in sessions_sorted:
            wpm = session.get("wpm", 0.0)
            accuracy = session.get("accuracy", 0.0)
            error = max(0.0, 1.0 - accuracy)
            timestamp = session.get("ended_at") or session.get("started_at") or ""
            human_time = _humanize_timestamp(timestamp)
            table.add_row(
                human_time,
                f"{wpm:.1f}",
                f"{accuracy * 100.0:.1f}%",
                f"{error * 100.0:.1f}%",
            )

        self.query_one("#stats-body", Static).update(Group(summary, table))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()


class TypingTutorApp(App):
    CSS = """
    #home, #session, #summary, #stats {
        padding: 1 2;
    }

    #title {
        content-align: center middle;
        text-style: bold;
    }

    #subtitle {
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 1;
    }

    #home-buttons, #session-buttons {
        height: auto;
        margin-top: 1;
    }

    #lesson-text {
        height: 12;
        border: solid $primary;
        padding: 1;
        overflow: auto;
    }

    #typing-area {
        height: 10;
        border: solid $secondary;
        padding: 1;
    }

    #metrics {
        height: auto;
        margin: 1 0;
    }

    #summary-title, #stats-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    TITLE = "Typing Tutor"

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


if __name__ == "__main__":
    TypingTutorApp().run()
