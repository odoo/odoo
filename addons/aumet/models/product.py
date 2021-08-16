# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    scientific_name = fields.Many2one('aumet.scientific_name', string='Scientific Name', required=False)
    marketplace_reference = fields.Integer()
    marketplace_seller_reference = fields.Integer()
    marketplace_referenced = fields.Boolean(compute='compute_referenced')
    marketplace_payment_method = fields.Many2many

    _sql_constraints = [
        ('marketplace_reference_unique', 'unique(marketplace_reference)', "Can't be duplicate value for this field!")
    ]

    @api.model
    def create(self, vals_list):
        if not vals_list["company_id"]:
            vals_list["company_id"] = self.env.company.id

        return super(ProductTemplate, self).create(vals_list)

    @api.depends('marketplace_reference')
    def compute_referenced(self):
        self.marketplace_referenced = True if self.marketplace_reference else False
