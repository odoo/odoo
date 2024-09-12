from . import models

from odoo import api, SUPERUSER_ID


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    all_fp = env["account.fiscal.position"].search([])
    for fp in all_fp:
        if not fp.fiscal_country_id:
            fp.write({"fiscal_country_id": fp.country_id})
