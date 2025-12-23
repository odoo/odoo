from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def _safe_ref(env, xml_id: str):
    try:
        return env.ref(xml_id, raise_if_not_found=False)
    except Exception:
        return None


def _ensure_currency_active(env, currency_xml_id: str) -> None:
    currency = _safe_ref(env, currency_xml_id)
    if not currency:
        _logger.warning("Currency XML ID not found: %s", currency_xml_id)
        return

    if hasattr(currency, "active") and not currency.active:
        currency.active = True
        _logger.info("Enabled currency: %s", currency_xml_id)


def ensure_currencies(env) -> None:
    """
    Ensures ViaFronteira default currencies are enabled:
    USD, BRL, ARS, PYG.
    """
    _logger.info("Ensuring default currencies are enabled...")
    for currency_xml_id in ["base.USD", "base.BRL", "base.ARS", "base.PYG"]:
        _ensure_currency_active(env, currency_xml_id)