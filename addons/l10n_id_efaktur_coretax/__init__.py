# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo import api, SUPERUSER_ID

def _post_init_hook(cr, registry):
    # When installed, should create the luxury tax group with specific XML ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    if not env.ref("l10n_id.l10n_id_tax_group_luxury_goods", raise_if_not_found=False):
        env['ir.model.data'].create({
            "name": "l10n_id_tax_group_luxury_goods",
            "module": "l10n_id",
            "model": "account.tax.group",
            "res_id": env['account.tax.group'].create({'name': 'Luxury Good Taxes (ID)'}).id,
            'noupdate': True
        })
