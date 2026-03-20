# Multi Lingua Playground

A personal, local-first language learning app focused on Traditional Chinese (native) plus improving English (IELTS ~6.5) and Japanese (JLPT N4-N5).

Built for quick use during work: news reading with translation, interactive practice, grammar explanations, and (planned) real-time YouTube live audio transcription.

Currently powered by Qwen3-14B (quantized GGUF) running locally via llama.cpp.

## Features (current & planned)

- [x] Instant translation (EN <-> JP <-> ZH-TW) with explanations
- [x] Daily news reading via RSS + side-by-side translation + notes
- [ ] Mini practice (cloze + multiple choice)
- [ ] Grammar explanations and targeted exercises
- [ ] Real-time YouTube live translation (audio transcription planned for V1)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. download opensource model
python ./script/download_model.py

# 3. create .env
echo LLM_MODEL=models/HY-MT1.5-7B-Q4_K_M.gguf > .env

# 4. Run the app
python app.py
```
