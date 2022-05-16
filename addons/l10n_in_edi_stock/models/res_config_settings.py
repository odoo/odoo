# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_edi_stock_username = fields.Char("Indian EDI Stock username",
        related="company_id.l10n_in_edi_stock_username", readonly=False)
    l10n_in_edi_stock_password = fields.Char("Indian EDI Stock password",
        related="company_id.l10n_in_edi_stock_password", readonly=False)
    l10n_in_edi_stock_production_env = fields.Boolean(
        string="Indian EDI Stock Testing Environment",
        related="company_id.l10n_in_edi_stock_production_env",
        readonly=False
    )

    def l10n_in_edi_stock_test(self):
        self.env["stock.picking"]._l10n_in_edi_stock_authenticate(self.company_id)
