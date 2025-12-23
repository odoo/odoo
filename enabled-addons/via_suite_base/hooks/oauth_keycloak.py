from __future__ import annotations

import os
import logging
from typing import Optional

_logger = logging.getLogger(__name__)


def _env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_ref(env, xml_id: str):
    try:
        return env.ref(xml_id, raise_if_not_found=False)
    except Exception:
        return None


def configure_keycloak_oauth_provider(env) -> None:
    """
    Configures Keycloak OAuth provider endpoints using environment variables.

    Expected ENV VARS:
      - VIA_KEYCLOAK_BASE_URL (e.g. https://auth.viafronteira.app)
      - VIA_KEYCLOAK_REALM (e.g. viafronteira)
      - VIA_KEYCLOAK_CLIENT_ID (e.g. via-suite)
      - VIA_KEYCLOAK_ENABLED (true/false)
      - VIA_KEYCLOAK_SCOPE (optional, default: "openid profile email")

    Notes:
      - This does NOT set secrets (client_secret). Secrets must not be committed.
      - It updates the record created by XML: via_suite_base.via_oauth_provider_keycloak
    """
    provider = _safe_ref(env, "via_suite_base.via_oauth_provider_keycloak")
    if not provider:
        _logger.warning("Keycloak OAuth provider record not found (via_suite_base.via_oauth_provider_keycloak).")
        return

    keycloak_base_url = os.getenv("VIA_KEYCLOAK_BASE_URL")
    keycloak_realm = os.getenv("VIA_KEYCLOAK_REALM")
    keycloak_client_id = os.getenv("VIA_KEYCLOAK_CLIENT_ID")
    keycloak_enabled = os.getenv("VIA_KEYCLOAK_ENABLED")
    keycloak_scope = os.getenv("VIA_KEYCLOAK_SCOPE") or "openid profile email"

    if keycloak_base_url and keycloak_realm:
        base_url = keycloak_base_url.rstrip("/")
        realm = keycloak_realm.strip()

        # Odoo auth_oauth fields (Odoo 19):
        # - auth_endpoint
        # - data_endpoint (token)
        # - validation_endpoint (userinfo)
        provider.auth_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
        provider.data_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
        provider.validation_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/userinfo"

        _logger.info("Keycloak endpoints configured: base_url=%s realm=%s", base_url, realm)
    else:
        _logger.warning("Missing VIA_KEYCLOAK_BASE_URL or VIA_KEYCLOAK_REALM; skipping endpoint configuration.")

    if keycloak_client_id:
        provider.client_id = keycloak_client_id
        _logger.info("Keycloak client_id configured: %s", keycloak_client_id)

    if hasattr(provider, "scope") and keycloak_scope:
        provider.scope = keycloak_scope
        _logger.info("Keycloak scope configured: %s", keycloak_scope)

    if keycloak_enabled is not None:
        provider.enabled = _env_bool(keycloak_enabled, default=True)
        _logger.info("Keycloak provider enabled set to: %s", provider.enabled)