from __future__ import annotations

def compute_correct_chars(target_text: str, typed_text: str) -> int:
    correct = 0
    for i, ch in enumerate(typed_text):
        if i >= len(target_text):
            break
        if ch == target_text[i]:
            correct += 1
    return correct


def compute_metrics(target_text: str, typed_text: str, elapsed_s: float) -> dict:
    total_typed = len(typed_text)
    correct_chars = compute_correct_chars(target_text, typed_text)
    accuracy = (correct_chars / total_typed) if total_typed > 0 else 0.0
    minutes = max(elapsed_s / 60.0, 1e-9)
    wpm = (correct_chars / 5.0) / minutes

    return {
        "total_typed": total_typed,
        "correct_chars": correct_chars,
        "accuracy": accuracy,
        "wpm": wpm,
    }
