# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_be_codabox_fiduciary_vat = fields.Char(related="company_id.l10n_be_codabox_fiduciary_vat", readonly=False)
    l10n_be_codabox_iap_token = fields.Char(related="company_id.l10n_be_codabox_iap_token", readonly=False)
    l10n_be_codabox_is_connected = fields.Boolean(related="company_id.l10n_be_codabox_is_connected")
    l10n_be_codabox_soda_journal = fields.Many2one(related="company_id.l10n_be_codabox_soda_journal", readonly=False)

    def l10n_be_codabox_connect(self):
        self.ensure_one()
        return self.company_id._l10n_be_codabox_connect()

    def l10n_be_codabox_revoke(self):
        self.ensure_one()
        return self.company_id._l10n_be_codabox_revoke()
