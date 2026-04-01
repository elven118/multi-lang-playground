import os
from pathlib import Path
from llama_cpp import Llama

_llm = None

def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default

def _env_str(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default

def _repo_root():
    return Path(__file__).resolve().parents[4]

def _resolve_model_path():
    env_path = os.getenv("LLM_MODEL_PATH") or os.getenv("LLM_MODEL")
    if env_path:
        candidate = Path(env_path).expanduser()
        if not candidate.is_absolute():
            candidate = (_repo_root() / candidate).resolve()
        return candidate
    return _repo_root() / "models" / "Qwen3.5-35B-A3B-Q4_K_M.gguf"

def _available_models():
    models_dir = _repo_root() / "models"
    if not models_dir.exists():
        return []
    return sorted([p.name for p in models_dir.glob("*.gguf")])

def _parse_fallbacks():
    raw = os.getenv("LLM_MODEL_FALLBACKS", "")
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]

def _init_llm(path, n_gpu_layers, n_ctx, n_threads, n_batch):
    chat_format = _env_str("LLM_CHAT_FORMAT")
    if chat_format and chat_format.lower() in {"auto", "default", "none"}:
        chat_format = None
    return Llama(
        model_path=str(path),
        n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_batch=n_batch,
        chat_format=chat_format,
        verbose=False
    )

def load_model():
    global _llm
    if _llm is None:
        path = _resolve_model_path()
        if not path.exists():
            available = _available_models()
            hint = f" Available models: {', '.join(available)}." if available else ""
            raise FileNotFoundError(
                f"Model file not found at {path}.{hint} "
                "Set LLM_MODEL_PATH or LLM_MODEL to override."
            )
        n_gpu_layers = _env_int("LLM_N_GPU_LAYERS", -1)
        n_ctx = _env_int("LLM_N_CTX", 4096)
        n_threads = _env_int("LLM_N_THREADS", 10)
        n_batch = _env_int("LLM_N_BATCH", 4096)
        try:
            _llm = _init_llm(path, n_gpu_layers, n_ctx, n_threads, n_batch)
        except ValueError as exc:
            if n_gpu_layers != 0:
                try:
                    _llm = _init_llm(path, 0, n_ctx, n_threads, n_batch)
                    return _llm
                except ValueError:
                    pass
            # Try fallbacks if provided or other models exist
            tried = {path.name}
            fallbacks = _parse_fallbacks()
            if not fallbacks:
                fallbacks = _available_models()
            for name in fallbacks:
                if name in tried:
                    continue
                candidate = path.parent / name
                if not candidate.exists():
                    continue
                try:
                    _llm = _init_llm(candidate, 0, n_ctx, n_threads, n_batch)
                    return _llm
                except ValueError:
                    tried.add(name)
                    continue
            raise ValueError(
                f"Failed to load model at {path} (and fallbacks). "
                "Try a smaller model via LLM_MODEL or set LLM_N_GPU_LAYERS=0."
            ) from exc
    return _llm

def generate(messages, max_tokens=4096, temperature=0.7, stream=False):
    llm = load_model()
    return llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
        stream=stream
    )

def generate_stream(messages, max_tokens=512, temperature=0.3):
    llm = load_model()
    return llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
        stream=True
    )
