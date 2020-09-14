# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('can_be_expensed')
    def _compute_visible_expense_policy(self):
        super(ProductTemplate, self)._compute_visible_expense_policy()
        expense_products = self.filtered(lambda p: p.can_be_expensed)
        if self.user_has_groups('hr_expense.group_hr_expense_user'):
            # If not, the value assigned by the super call is the correct one.
            expense_products.visible_expense_policy = True
