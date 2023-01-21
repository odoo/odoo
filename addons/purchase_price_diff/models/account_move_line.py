# -*- coding: utf-8 -*-

from odoo import models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_price_diff_account(self):
        self.ensure_one()
        if self.product_id.cost_method == 'standard':
            debit_pdiff_account = self.product_id.property_account_creditor_price_difference \
                                    or self.product_id.categ_id.property_account_creditor_price_difference_categ
            debit_pdiff_account = self.move_id.fiscal_position_id.map_account(debit_pdiff_account)
            return debit_pdiff_account
        return super()._get_price_diff_account()
