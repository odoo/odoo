# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountDisallowedExpensesCategory(models.Model):
    _inherit = 'account.disallowed.expenses.category'

    car_category = fields.Boolean('Make Vehicle Required', help='The vehicle becomes mandatory while booking any account move.')

    @api.depends('car_category')
    def _compute_display_name(self):
        super()._compute_display_name()
        # Do not display the rate in the name for car expenses
        for category in self:
            if category.car_category:
                category.display_name = f'{category.code} - {category.name}'
