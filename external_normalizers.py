import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import lru_cache


GEMINI_MODEL = "gemini-3.5-flash"
IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
GEMINI_TIMEOUT_SECONDS = 2.5
IBGE_TIMEOUT_SECONDS = 2.0
GEMINI_MAX_INPUT_CHARS = 1000
GEMINI_MAX_OUTPUT_CHARS = 1200

_GEMINI_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_GEMINI_CLIENT = None
_STATS = {
    "gemini_calls": 0,
    "ibge_calls": 0,
}

_SIMPLE_STANDARD_ANSWERS = {
    "s",
    "sim",
    "ss",
    "n",
    "nao",
    "nao sei",
    "n sei",
    "nao tenho certeza",
    "talvez",
    "um pouco",
    "pouco",
    "muito",
    "muita",
    "nenhum",
    "nenhuma",
    "nada",
    "leve",
    "moderado",
    "moderada",
    "forte",
    "intenso",
    "intensa",
}

_INFORMAL_HINTS = {
    "agr",
    "hr",
    "mt",
    "mto",
    "mta",
    "ta",
    "to",
    "pra",
    "pro",
    "krl",
    "caralho",
    "pqp",
    "nn",
    "ss",
}


def reset_stats():
    _STATS["gemini_calls"] = 0
    _STATS["ibge_calls"] = 0


def get_stats():
    return dict(_STATS)


def _normalize_basic(value):
    import symptom_ai

    return symptom_ai.normalize_text(value or "")


def should_normalize_with_gemini(text):
    text = (text or "").strip()
    if not text:
        return False

    normalized = _normalize_basic(text)
    if normalized in _SIMPLE_STANDARD_ANSWERS:
        return False

    words = normalized.split()
    if len(words) <= 3 and not any(word in _INFORMAL_HINTS for word in words):
        return False

    return any(word in _INFORMAL_HINTS for word in words) or len(text) >= 80


def _get_gemini_client():
    global _GEMINI_CLIENT

    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    from dotenv import load_dotenv
    from google import genai

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    _GEMINI_CLIENT = genai.Client(api_key=api_key)
    return _GEMINI_CLIENT


def _call_gemini_normalizer(text):
    text = (text or "").strip()[:GEMINI_MAX_INPUT_CHARS]
    client = _get_gemini_client()
    if not client:
        return text

    _STATS["gemini_calls"] += 1
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"""
Voce e um normalizador de linguagem informal em portugues brasileiro.

Sua unica funcao e transformar o texto recebido em portugues brasileiro
claro e padronizado, preservando exatamente o significado original.

Regras obrigatorias:
- Entenda abreviacoes e girias brasileiras.
- Corrija erros de digitacao e falta de acentos.
- Entenda linguagem coloquial.
- Entenda palavroes usados para indicar intensidade.
- Padronize verbos coloquiais de sintomas em termos clinicos comuns quando
  isso preservar o mesmo significado, por exemplo "esta inchando" como
  "esta com inchaco".
- Preserve exatamente o significado original.
- Nao invente informacoes.
- Nao remova informacoes.
- Nao invente sintomas.
- Nao altere a intensidade informada pelo usuario.
- Preserve respostas curtas como sim, nao, nao sei e equivalentes.
- Nao faca diagnostico.
- Nao de conselhos.
- Nao de explicacoes.
- Nao de alternativas.
- Nao use Markdown.
- Retorne SOMENTE o texto normalizado.

Texto:
{text}
""",
    )
    normalized = (getattr(response, "text", "") or "").strip()
    if not normalized:
        return text
    if len(normalized) > min(GEMINI_MAX_OUTPUT_CHARS, max(len(text) * 2, len(text) + 300)):
        return text
    if any(marker in normalized.lower() for marker in ("```", "<script", "</", "javascript:")):
        return text
    return normalized


@lru_cache(maxsize=256)
def normalize_user_text_with_gemini(text):
    text = (text or "").strip()[:GEMINI_MAX_INPUT_CHARS]
    if not text:
        return text
    if not should_normalize_with_gemini(text):
        return text

    try:
        future = _GEMINI_EXECUTOR.submit(_call_gemini_normalizer, text)
        return future.result(timeout=GEMINI_TIMEOUT_SECONDS)
    except (Exception, TimeoutError):
        return text


@lru_cache(maxsize=1)
def fetch_ibge_municipios():
    import requests

    _STATS["ibge_calls"] += 1
    response = requests.get(IBGE_MUNICIPIOS_URL, timeout=IBGE_TIMEOUT_SECONDS)
    response.raise_for_status()
    municipios = response.json()
    return municipios if isinstance(municipios, list) else []


@lru_cache(maxsize=256)
def normalize_ibge_location(city, state):
    city = (city or "").strip()
    state = (state or "").strip()
    if not city:
        return None

    try:
        import symptom_ai

        normalized_city = symptom_ai.normalize_text(city)
        normalized_state = symptom_ai.normalize_text(state)
        state_alias = symptom_ai.STATE_ALIASES.get(normalized_state, state)
        normalized_state_alias = symptom_ai.normalize_text(state_alias)

        for municipio in fetch_ibge_municipios():
            if symptom_ai.normalize_text(municipio.get("nome")) != normalized_city:
                continue

            uf = municipio["microrregiao"]["mesorregiao"]["UF"]
            estado = uf.get("nome", "")
            sigla = uf.get("sigla", "")
            regiao = (uf.get("regiao") or {}).get("nome", "")

            if normalized_state and normalized_state not in {
                symptom_ai.normalize_text(estado),
                symptom_ai.normalize_text(sigla),
                normalized_state_alias,
            }:
                continue

            return {
                "city": municipio.get("nome", city),
                "state": estado or state,
                "uf": sigla,
                "region": regiao,
            }
    except Exception:
        return None

    return None
