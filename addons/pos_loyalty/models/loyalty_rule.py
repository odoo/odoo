# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import ustr

class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    valid_product_ids = fields.Many2many(
        'product.product', "Valid Products", compute='_compute_valid_product_ids',
        help="These are the products that are valid for this rule.")
    any_product = fields.Boolean(
        compute='_compute_valid_product_ids', help="Technical field, whether all product match")

    promo_barcode = fields.Char("Barcode", compute='_compute_promo_barcode', store=True, readonly=False,
        help="A technical field used as an alternative to the promo code. "
        "This is automatically generated when the promo code is changed."
    )

    @api.depends('product_ids', 'product_category_id', 'product_tag_id') #TODO later: product tags
    def _compute_valid_product_ids(self):
        domain_products = {}
        for rule in self:
            if rule.product_ids or\
                rule.product_category_id or\
                rule.product_tag_id or\
                rule.product_domain not in ('[]', "[['sale_ok', '=', True]]"):
                domain = rule._get_valid_product_domain()
                domain = expression.AND([[('available_in_pos', '=', True)], domain])
                product_ids = domain_products.get(ustr(domain))
                if product_ids is None:
                    product_ids = self.env['product.product'].search(domain, order="id")
                    domain_products[ustr(domain)] = product_ids
                rule.valid_product_ids = product_ids
                rule.any_product = False
            else:
                rule.any_product = True
                rule.valid_product_ids = self.env['product.product']

    @api.depends('code')
    def _compute_promo_barcode(self):
        for rule in self:
            rule.promo_barcode = self.env['loyalty.card']._generate_code()
