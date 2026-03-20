def build_translation_messages(text, source_lang, target_lang, explain=False):
    explain_hint = (
        "After the translation, add 3-5 short bullet notes about key vocabulary or grammar."
        if explain else
        "Return the translation. Preserve line breaks."
    )
    system = (
        "You are a careful translator and language tutor. "
        "Do not include analysis or internal reasoning. "
        "Keep output concise and learner-friendly. "
        "Preserve the original line breaks. "
    )
    user = (
        f"Translate from {source_lang} to {target_lang}.\n"
        f"Text: {text}\n"
        f"{explain_hint}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
