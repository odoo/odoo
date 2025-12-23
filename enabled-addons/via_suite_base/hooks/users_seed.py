from __future__ import annotations

import logging
from typing import Iterable

_logger = logging.getLogger(__name__)


def _upsert_user(env, *, name: str, login: str, email: str, tz: str, lang: str) -> int:
    users = env["res.users"].sudo()

    user = users.search([("login", "=", login)], limit=1)
    values = {
        "name": name,
        "login": login,
        "email": email,
        "active": True,
        "tz": tz,
        "lang": lang,
    }

    # company fields mudam menos, mas mantém defensivo:
    main_company = env.ref("base.main_company", raise_if_not_found=False)
    if main_company:
        if "company_id" in users._fields:
            values["company_id"] = main_company.id
        if "company_ids" in users._fields:
            values["company_ids"] = [(4, main_company.id)]

    if user:
        user.write(values)
        _logger.info("Updated user: %s", login)
        return user.id

    created = users.create(values)
    _logger.info("Created user: %s", login)
    return created.id


def ensure_default_admin_users_exist(env) -> None:
    """
    Creates/updates Via default admin users idempotently.
    """
    _logger.info("Ensuring default Via admin users exist (upsert)...")

    _upsert_user(
        env,
        name="Rodrigo Fraga",
        login="rodrigo.fraga@viafronteira.com",
        email="rodrigo.fraga@viafronteira.com",
        tz="America/Sao_Paulo",
        lang="pt_BR",
    )

    _upsert_user(
        env,
        name="Oscar Gomes",
        login="oscar.gomes@viafronteira.com",
        email="oscar.gomes@viafronteira.com",
        tz="America/Sao_Paulo",
        lang="pt_BR",
    )

    _upsert_user(
        env,
        name="Nelson Oliveira",
        login="nelson.oliveira@viafronteira.com",
        email="nelson.oliveira@viafronteira.com",
        tz="America/Sao_Paulo",
        lang="pt_BR",
    )