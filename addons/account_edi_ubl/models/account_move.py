# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import float_repr


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_ubl_values(self):
        def format_monetary(amount):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(amount, self.currency_id.decimal_places)

        return {
            'invoice': self,
            'ubl_version': 2.1,
            'type_code': 380 if self.move_type == 'out_invoice' else 381,
            'payment_means_code': 42 if self.journal_id.bank_account_id else 31,
            'format_monetary': format_monetary,
        }
