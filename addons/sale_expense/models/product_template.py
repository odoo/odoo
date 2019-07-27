# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _compute_visible_expense_policy(self):
        super(ProductTemplate, self)._compute_visible_expense_policy()

        visibility = self.user_has_groups('hr_expense.group_hr_expense_user')
        for product_template in self:
            if not product_template.visible_expense_policy:
                product_template.visible_expense_policy = visibility
