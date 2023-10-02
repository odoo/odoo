# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_hu_nav_credential_ids = fields.One2many(
        related="company_id.l10n_hu_nav_credential_ids",
        string="NAV Credentials",
        readonly=False,
    )
    l10n_hu_production_cred = fields.Boolean(related="company_id.l10n_hu_production_cred", string="PRODUCTION USAGE")
    l10n_hu_use_demo_mode = fields.Boolean(
        related="company_id.l10n_hu_use_demo_mode", readonly=False, string="Demo mode?"
    )
    l10n_hu_company_tax_arrangments = fields.Selection(
        related="company_id.l10n_hu_company_tax_arrangments", readonly=False
    )
