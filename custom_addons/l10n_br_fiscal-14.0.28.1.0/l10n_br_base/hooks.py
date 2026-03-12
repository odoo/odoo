# Copyright (C) 2019-2020 - Raphael Valyi Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _ensure_exclusive_modules(env_or_cr, module_name, conflicting_modules, family_label):
    cr = getattr(env_or_cr, "cr", env_or_cr)
    names = sorted({name for name in conflicting_modules if name and name != module_name})
    cr.execute(
        """
        SELECT name, state
        FROM ir_module_module
        WHERE name = ANY(%s)
          AND state IN %s
        ORDER BY name
        """,
        (names, ("installed", "to install", "to upgrade")),
    )
    conflicts = cr.fetchall()
    if not conflicts:
        return
    details = ", ".join(f"{name} ({state})" for name, state in conflicts)
    raise UserError(
        "Cannot install module '%s' because this database already has conflicting %s modules: %s. "
        "Keep only one stack from this family installed per database."
        % (module_name, family_label, details)
    )


def pre_init_hook(cr):
    """
    The objective of this hook is to ensure the Brazil country is
    translated as "Brasil" in pt_BR to get the NFe tests pass
    even if the pt_BR language pack is not installed.
    """
    _ensure_exclusive_modules(
        cr,
        "l10n_br_base",
        [
            "l10n_br",
            "l10n_br_sales",
            "l10n_br_website_sale",
        ],
        "Brazil localization baseline",
    )
    cr.execute(
        """SELECT id
    FROM ir_translation
    WHERE name='res.country,name' AND
    lang='pt_BR'"""
    )
    if not cr.fetchone():
        env = api.Environment(cr, SUPERUSER_ID, {})
        brazil_country_id = env.ref("base.br").id
        insert_query = """
        INSERT INTO ir_translation (
            name,
            res_id,
            lang,
            type,
            src,
            value,
            module,
            state)
        VALUES (
            'res.country,name',
            %s,
            'pt_BR',
            'model',
            'Brazil',
            'Brasil',
            'base',
            'translated');
        """
        cr.execute(insert_query, (brazil_country_id,))
