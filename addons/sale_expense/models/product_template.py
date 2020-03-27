# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_visible_expense_policy(self):
        visibility = self.user_has_groups('hr_expense.group_hr_expense_user')
        return visibility or super(ProductTemplate, self)._default_visible_expense_policy()

    @api.depends('can_be_expensed')
    def _compute_visible_expense_policy(self):
        expense_products = self.filtered(lambda p: p.can_be_expensed)
        for product_template in self - expense_products:
            product_template.visible_expense_policy = False

        super(ProductTemplate, expense_products)._compute_visible_expense_policy()
        visibility = self.user_has_groups('hr_expense.group_hr_expense_user')
        for product_template in expense_products:
            if not product_template.visible_expense_policy:
                product_template.visible_expense_policy = visibility
