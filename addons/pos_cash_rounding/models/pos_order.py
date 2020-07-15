# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import float_is_zero, float_round

class PosOrder(models.Model):
    _inherit = "pos.order"


    def _get_rounded_amount(self, amount):
        if self.config_id.cash_rounding:
            amount = float_round(amount, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
        return super(PosOrder, self)._get_rounded_amount(amount)

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()
        vals['invoice_cash_rounding_id'] = self.config_id.rounding_method.id
        return vals

    def _get_amount_receivable(self):
        if self.config_id.cash_rounding:
            return self.amount_paid
        return super(PosOrder, self)._get_amount_receivable()
