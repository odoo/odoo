# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_sale_expense_products(self):
        product_data = [
            self.env.ref('hr_expense.food_expense_product', False),
            self.env.ref('hr_expense.mileage_expense_product', False),
            self.env.ref('hr_expense.accomodation_expense_product', False),
            self.env.ref('hr_expense.allowance_expense_product', False)
        ]
        for product in self.filtered(lambda p: p in product_data):
            raise UserError(_(
                "You cannot delete %(name)s as it is used in 'Sales Expense'."
                "Please archive it instead.",
                name=product.name
            ))
