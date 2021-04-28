# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = ['loyalty.rule']

    valid_product_ids = fields.One2many('product.product', compute='_compute_valid_product_ids')

    @api.depends('rule_domain')
    def _compute_valid_product_ids(self):
        for rule in self:
            rule.valid_product_ids = self.env['product.product'].search(
                safe_eval(rule.rule_domain) if rule.rule_domain else []
            )

    def is_product_valid(self, product_id):
        """Avoid fetching the full product list if no domain is defined"""
        if self.rule_domain:
            return product_id in self.valid_product_ids
        return True
