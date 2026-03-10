# Copyright (C) 2019-2020 - Raphael Valyi Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to ensure the Brazil country is
    translated as "Brasil" in pt_BR to get the NFe tests pass
    even if the pt_BR language pack is not installed.
    """
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
