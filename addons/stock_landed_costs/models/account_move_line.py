# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _get_cost_line_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.product_id.name,
            'account_id': self.product_id.product_tmpl_id.get_product_accounts()[
                'stock_input'].id,
            'price_unit': self.currency_id._convert(
                self.price_subtotal,
                self.company_currency_id,
                self.company_id,
                self.move_id.date),
            'split_method': 'equal',
        }
