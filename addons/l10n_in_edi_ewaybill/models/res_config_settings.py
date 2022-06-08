# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_edi_ewaybill_username = fields.Char("Indian EDI Stock username",
        related="company_id.l10n_in_edi_ewaybill_username", readonly=False)
    l10n_in_edi_ewaybill_password = fields.Char("Indian EDI Stock password",
        related="company_id.l10n_in_edi_ewaybill_password", readonly=False)

    def l10n_in_edi_ewaybill_test(self):
        self.env["account.edi.format"]._l10n_in_edi_ewaybill_authenticate(self.company_id)
