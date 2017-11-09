# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange('can_be_expensed')
    def _onchange_can_be_expensed(self):
        if not self.can_be_expensed:
            self.expense_policy = 'no'
