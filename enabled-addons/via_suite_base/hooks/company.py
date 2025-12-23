from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def _safe_ref(env, xml_id: str):
    try:
        return env.ref(xml_id, raise_if_not_found=False)
    except Exception:
        return None


def ensure_company_currency_usd(env) -> None:
    """
    Sets the main company base currency to USD (defensive).
    """
    company = _safe_ref(env, "base.main_company")
    usd = _safe_ref(env, "base.USD")

    if not company or not usd:
        _logger.warning(
            "Cannot set company currency to USD (missing refs: company=%s usd=%s)",
            bool(company),
            bool(usd),
        )
        return

    if hasattr(company, "currency_id") and company.currency_id != usd:
        company.currency_id = usd
        _logger.info("Main company currency set to USD.")