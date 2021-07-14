# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    scientific_name = fields.Many2one('aumet.scientific_name', string='Scientific Name', required=False)

    @api.model
    def create(self, vals_list):
        if not vals_list["company_id"]:
            vals_list["company_id"] = self.env.company.id

        return super(ProductTemplate, self).create(vals_list)
