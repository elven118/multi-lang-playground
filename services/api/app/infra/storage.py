"""Simple local JSON storage for user preferences and progress."""

import json
import os

DEFAULT_STATE = {
    "target_lang": "Japanese",
    "explain": False
}


def _state_path():
    os.makedirs("data", exist_ok=True)
    return os.path.join("data", "state.json")


def load_state():
    path = _state_path()
    if not os.path.exists(path):
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE.copy()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    path = _state_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
