import os
from dotenv import load_dotenv


def get_config():
    """Load from local .env first, then global ~/.codeneura/config.env"""
    local_env = os.path.join(os.getcwd(), '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env, override=True)

    has_key = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")

    if not has_key:
        global_config = os.path.expanduser("~/.codeneura/config.env")
        if os.path.exists(global_config):
            load_dotenv(global_config, override=True)

    return {
        'provider': os.getenv("LLM_PROVIDER", "groq").lower(),
        'api_key': os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY"),
        'model': os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    }


def call_llm(prompt, max_tokens=500):
    config = get_config()
    provider = config['provider']
    api_key = config['api_key']
    model = config['model']

    if provider == "groq":
        return _call_groq(api_key, model, prompt, max_tokens)
    elif provider == "openai":
        return _call_openai(api_key, model, prompt, max_tokens)
    elif provider == "anthropic":
        return _call_anthropic(api_key, model, prompt, max_tokens)
    elif provider == "google":
        return _call_google(api_key, model, prompt, max_tokens)
    elif provider == "ollama":
        return _call_ollama(model, prompt, max_tokens)
    else:
        return _call_groq(api_key, model, prompt, max_tokens)


def _try_models(model, fallback_list, call_fn):
    """Generic fallback runner — tries the configured model first, then known-stable alternatives."""
    models_to_try = [model] + [m for m in fallback_list if m != model]
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

    last_error = None
    for try_model in models_to_try:
        try:
            return call_fn(try_model)
        except Exception as e:
            last_error = e
            continue

    return f"Could not get AI response — all models unavailable: {str(last_error)}"


def _call_groq(api_key, model, prompt, max_tokens):
    from groq import Groq
    client = Groq(api_key=api_key)

    fallback_list = ["openai/gpt-oss-120b", "llama-3.1-8b-instant", "qwen3.6-27b"]

    def call_fn(m):
        response = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0
        )
        return response.choices[0].message.content

    return _try_models(model, fallback_list, call_fn)


def _call_openai(api_key, model, prompt, max_tokens):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    fallback_list = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

    def call_fn(m):
        response = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0
        )
        return response.choices[0].message.content

    return _try_models(model, fallback_list, call_fn)


def _call_anthropic(api_key, model, prompt, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    fallback_list = ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]

    def call_fn(m):
        response = client.messages.create(
            model=m,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    return _try_models(model, fallback_list, call_fn)


def _call_google(api_key, model, prompt, max_tokens):
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    fallback_list = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

    def call_fn(m):
        gemini = genai.GenerativeModel(m)
        response = gemini.generate_content(prompt)
        return response.text

    return _try_models(model, fallback_list, call_fn)


def _call_ollama(model, prompt, max_tokens):
    import requests

    fallback_list = ["llama3.2", "codellama", "deepseek-coder"]

    def call_fn(m):
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": m, "prompt": prompt, "stream": False}
        )
        result = response.json().get("response", "")
        if not result:
            raise ValueError(f"Empty response from Ollama model {m}")
        return result

    return _try_models(model, fallback_list, call_fn)