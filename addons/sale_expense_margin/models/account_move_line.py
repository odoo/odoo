# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale_expense


class AccountMoveLine(sale_expense.AccountMoveLine):

    def _sale_prepare_sale_line_values(self, order, price):
        res = super()._sale_prepare_sale_line_values(order, price)
        if self.expense_id:
            res['expense_id'] = self.expense_id.id
        return res
