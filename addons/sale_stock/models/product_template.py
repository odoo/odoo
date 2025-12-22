# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('type')
    def _compute_expense_policy(self):
        super()._compute_expense_policy()
        self.filtered(lambda t: t.is_storable).expense_policy = 'no'

    @api.depends('type')
    def _compute_service_type(self):
        super()._compute_service_type()
        self.filtered(lambda t: t.is_storable).service_type = 'manual'
