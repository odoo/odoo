from __future__ import annotations

import os
import logging
from typing import Optional, Iterable

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


def _ensure_currency_active(env, currency_xml_id: str) -> None:
    currency = _safe_ref(env, currency_xml_id)
    if not currency:
        _logger.warning("Currency XML ID not found: %s", currency_xml_id)
        return
    if not getattr(currency, "active", False):
        currency.active = True
        _logger.info("Enabled currency: %s", currency_xml_id)


def _ensure_company_currency_usd(env) -> None:
    company = _safe_ref(env, "base.main_company")
    usd = _safe_ref(env, "base.USD")
    if not company or not usd:
        _logger.warning("Cannot set company currency to USD (missing refs: company=%s usd=%s)", bool(company), bool(usd))
        return

    if company.currency_id != usd:
        company.currency_id = usd
        _logger.info("Main company currency set to USD.")


def _configure_keycloak_oauth_provider(env) -> None:
    provider = _safe_ref(env, "via_suite_base.via_oauth_provider_keycloak")
    if not provider:
        _logger.warning("Keycloak OAuth provider record not found (via_suite_base.via_oauth_provider_keycloak).")
        return

    keycloak_base_url = os.getenv("VIA_KEYCLOAK_BASE_URL")
    keycloak_realm = os.getenv("VIA_KEYCLOAK_REALM")
    keycloak_client_id = os.getenv("VIA_KEYCLOAK_CLIENT_ID")
    keycloak_enabled = os.getenv("VIA_KEYCLOAK_ENABLED")

    if keycloak_base_url and keycloak_realm:
        base_url = keycloak_base_url.rstrip("/")
        realm = keycloak_realm.strip()

        provider.auth_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
        provider.data_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
        provider.validation_endpoint = f"{base_url}/realms/{realm}/protocol/openid-connect/userinfo"

        _logger.info("Keycloak endpoints configured: base_url=%s realm=%s", base_url, realm)
    else:
        _logger.warning(
            "Keycloak env vars missing. Set VIA_KEYCLOAK_BASE_URL and VIA_KEYCLOAK_REALM to auto-configure endpoints."
        )

    if keycloak_client_id:
        provider.client_id = keycloak_client_id
        _logger.info("Keycloak client_id configured: %s", keycloak_client_id)

    if keycloak_enabled is not None:
        provider.enabled = _env_bool(keycloak_enabled, default=True)
        _logger.info("Keycloak provider enabled set to: %s", provider.enabled)


def _find_user_groups_field_name(env) -> Optional[str]:
    """
    Odoo 19 changed some fields; we avoid guessing.
    We discover the first Many2many field on res.users that points to res.groups.
    """
    user_model = env["res.users"]
    for field_name, field in user_model._fields.items():
        if getattr(field, "comodel_name", None) == "res.groups":
            return field_name
    return None


def _add_users_to_group(env, users, group) -> None:
    if not users or not group:
        return

    group_field_name = _find_user_groups_field_name(env)
    if not group_field_name:
        _logger.warning("Could not find a groups M2M field on res.users pointing to res.groups. Skipping group assignment.")
        return

    for user in users:
        if not user:
            continue
        try:
            user.write({group_field_name: [(4, group.id)]})
            _logger.info("Added user %s to group %s via field %s", user.login, group.name, group_field_name)
        except Exception as exc:
            _logger.exception("Failed to add user %s to group %s: %s", getattr(user, "login", "<?>"), group.name, exc)


def _ensure_default_admin_users_are_admins(env) -> None:
    via_admin_group = _safe_ref(env, "via_suite_base.via_group_admin")
    if not via_admin_group:
        _logger.warning("Via Admin group not found (via_suite_base.via_group_admin).")
        return

    rodrigo = _safe_ref(env, "via_suite_base.via_user_rodrigo_fraga")
    oscar = _safe_ref(env, "via_suite_base.via_user_oscar_gomes")
    nelson = _safe_ref(env, "via_suite_base.via_user_nelson_oliveira")

    users = [u for u in [rodrigo, oscar, nelson] if u]
    if not users:
        _logger.warning("No default Via admin users found (XML IDs missing).")
        return

    _add_users_to_group(env, users, via_admin_group)


def post_init_hook(env):
    """
    Odoo 19 post_init_hook signature: post_init_hook(env)

    This runs after module installation on a database, ideal for:
    - cross-version safe assignments (M2M fields that may rename)
    - environment-driven configuration (Keycloak endpoints)
    """

    _logger.info("Running via_suite_base post_init_hook...")

    # 1) Currencies (defensive)
    for currency_xml_id in ["base.USD", "base.BRL", "base.ARS", "base.PYG"]:
        _ensure_currency_active(env, currency_xml_id)

    # 2) Company base currency USD
    _ensure_company_currency_usd(env)

    # 3) Keycloak OAuth provider from env vars
    _configure_keycloak_oauth_provider(env)

    # 4) Ensure default Via admin users are admins
    _ensure_default_admin_users_are_admins(env)

    _logger.info("via_suite_base post_init_hook completed.")