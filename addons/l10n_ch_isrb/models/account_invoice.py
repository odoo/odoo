# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_isrb_id_number(self):
        """Return ISR-B Customer ID"""
        self.ensure_one()
        partner_bank = self.invoice_partner_bank_id
        return partner_bank.l10n_ch_isrb_id_number or ''
