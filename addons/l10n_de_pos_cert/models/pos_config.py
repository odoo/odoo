# -*- coding: utf-8 -*-

from odoo import models, _, fields
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'
    fiskaly_tss_id = fields.Char(string="TSS ID")
    fiskaly_client_id = fields.Char(string="Client ID")

    def _check_fiskaly_key_secret(self):
        if not self.company_id.fiskaly_key or not self.company_id.fiskaly_secret:
            raise UserError(_("You have to set your Fiskaly key and secret in your company settings."))

    def _check_fiskaly_tss_client_ids(self):
        if not self.fiskaly_tss_id or not self.fiskaly_client_id:
            raise UserError(_("You have to set your Fiskaly TSS ID and Client ID in your PoS settings."))

    def open_ui(self):
        self._check_fiskaly_key_secret()
        self._check_fiskaly_tss_client_ids()
        return super(PosConfig, self).open_ui()
