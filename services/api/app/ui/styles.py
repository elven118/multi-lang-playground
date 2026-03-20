from pathlib import Path

CSS_PATH = Path(__file__).resolve().parent / "styles.css"


def load_styles_html():
    css = CSS_PATH.read_text(encoding="utf-8")
    return f"<style>\n{css}\n</style>"
