# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_edi_username = fields.Char("Indian EDI username", related="company_id.l10n_in_edi_username", readonly=False)
    l10n_in_edi_password = fields.Char("Indian EDI password", related="company_id.l10n_in_edi_password", readonly=False)
    l10n_in_edi_production_env = fields.Boolean(
        string="Indian EDI Testing Environment",
        related="company_id.l10n_in_edi_production_env",
        readonly=False
    )

    def l10n_in_edi_test(self):
        self.env["account.edi.format"]._l10n_in_edi_authenticate(self.company_id)
        if not self.company_id.sudo()._l10n_in_edi_token_is_valid():
            raise UserError(_("Incorrect username or password, or the GST number on company does not match."))
