from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def load_template(name):
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")
