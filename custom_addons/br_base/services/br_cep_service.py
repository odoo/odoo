import logging

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


_LOGGER = logging.getLogger(__name__)


def fetch_cep(cep: str) -> dict | None:
    digits = "".join(char for char in (cep or "") if char.isdigit())
    if len(digits) != 8 or requests is None:
        return None
    url = f"https://viacep.com.br/ws/{digits}/json/"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover
        _LOGGER.info("Falha ao consultar ViaCEP: %s", exc)
        return None
    if payload.get("erro"):
        return None
    return {
        "logradouro": payload.get("logradouro"),
        "bairro": payload.get("bairro"),
        "localidade": payload.get("localidade"),
        "uf": payload.get("uf"),
        "ibge": payload.get("ibge"),
    }

