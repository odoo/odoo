# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_expensed = fields.Boolean(string="Can be Expensed", compute='_compute_can_be_expensed',
        store=True, readonly=False, help="Specify whether the product can be selected in an expense.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # When creating an expense product on the fly, you don't expect to
            # have taxes on it
            if vals.get('can_be_expensed', False) and not self.env.context.get('import_file'):
                vals.update({'supplier_taxes_id': False})
        return super(ProductTemplate, self).create(vals_list)

    @api.depends('type')
    def _compute_can_be_expensed(self):
        self.filtered(lambda p: p.type not in ['consu', 'service']).update({'can_be_expensed': False})
