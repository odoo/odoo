from __future__ import annotations

import logging
from typing import Optional

_logger = logging.getLogger(__name__)


DEFAULT_ADMIN_LOGINS = [
    "rodrigo.fraga@viafronteira.com",
    "oscar.gomes@viafronteira.com",
    "nelson.oliveira@viafronteira.com",
]


def _safe_ref(env, xml_id: str):
    try:
        return env.ref(xml_id, raise_if_not_found=False)
    except Exception:
        return None


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


def _find_users_by_logins(env, logins: list[str]):
    users_model = env["res.users"].sudo()
    if not logins:
        return users_model.browse([])
    return users_model.search([("login", "in", list(logins))])


def _add_users_to_group(env, users, group) -> None:
    if not users or not group:
        return

    group_field_name = _find_user_groups_field_name(env)
    if not group_field_name:
        _logger.warning(
            "Could not find a groups M2M field on res.users pointing to res.groups. Skipping group assignment."
        )
        return

    for user in users:
        if not user:
            continue
        try:
            user.write({group_field_name: [(4, group.id)]})
            _logger.info("Added user %s to group %s via field %s", user.login, group.name, group_field_name)
        except Exception as exc:
            _logger.exception(
                "Failed to add user %s to group %s: %s",
                getattr(user, "login", "<?>"),
                getattr(group, "name", "<?>"),
                exc,
            )


def ensure_default_admin_users_are_admins(env) -> None:
    """
    Ensures the default Via admin users belong to the Via Admin group.

    Depends only on:
      - via_suite_base.via_group_admin
      - Users existing in DB (created by users_seed.ensure_default_admin_users_exist)
        matching DEFAULT_ADMIN_LOGINS
    """
    via_admin_group = _safe_ref(env, "via_suite_base.via_group_admin")
    if not via_admin_group:
        _logger.warning("Via Admin group not found (via_suite_base.via_group_admin).")
        return

    users = _find_users_by_logins(env, DEFAULT_ADMIN_LOGINS)
    if not users:
        _logger.warning("No default Via admin users found by login: %s", DEFAULT_ADMIN_LOGINS)
        return

    _add_users_to_group(env, users, via_admin_group)