# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    rules_count = fields.Integer(compute='_compute_rules_count', string='# Analytic Rules')

    def _compute_rules_count(self):
        Analytic = self.env['account.analytic.default']
        for product in self:
            product.rules_count = Analytic.search_count([('product_id', '=', product.id)])


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rules_count = fields.Integer(compute='_compute_rules_count', string='# Analytic Rules')

    def _compute_rules_count(self):
        for template in self:
            template.rules_count = sum([p.rules_count for p in template.product_variant_ids])

    @api.multi
    def action_view_rules(self):
        result = self.env.ref('account_analytic_default.action_product_default_list').read()[0]
        result['domain'] = [('product_id', 'in', self.mapped('product_variant_ids').ids)]
        # Remove context so it is not going to filter on product_id with active_id of template
        result['context'] = "{}"
        return result
