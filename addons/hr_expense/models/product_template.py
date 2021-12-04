# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_expensed = fields.Boolean(string="Can be Expensed", help="Specify whether the product can be selected in an expense.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # When creating an expense product on the fly, you don't expect to
            # have taxes on it
            if vals.get('can_be_expensed', False) and not self.env.context.get('import_file'):
                vals.update({'supplier_taxes_id': False})
        return super(ProductTemplate, self).create(vals_list)

    @api.onchange('type')
    def _onchange_type_for_expense(self):
        if self.type not in ['consu', 'service']:  # storable can not be expensed.
            self.can_be_expensed = False
