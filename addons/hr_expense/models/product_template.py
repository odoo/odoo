# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _auto_init(self):
        if not column_exists(self.env.cr, "product_template", "can_be_expensed"):
            # In case of a big database with a lot of product tempaltes, the RAM gets exhausted
            # To prevent a process from being killed, we create the column 'can_be_expensed' manually
            # Then we do the computation in a query by setting can_be_expensed to false for consumables and services
            create_column(self.env.cr, "product_template", "can_be_expensed", "boolean")
            self.env.cr.execute("""
                UPDATE product_template product
                SET can_be_expensed = false
                WHERE product.type not in ('consu', 'service')
                """)
        return super()._auto_init()

    can_be_expensed = fields.Boolean(string="Can be Expensed", compute='_compute_can_be_expensed',
        store=True, readonly=False, help="Specify whether the product can be selected in an expense.")

    @api.model
    def default_get(self, fields):
        result = super(ProductTemplate, self).default_get(fields)
        if self.env.context.get('default_can_be_expensed'):
            result['supplier_taxes_id'] = False
        return result

    @api.depends('type')
    def _compute_can_be_expensed(self):
        self.filtered(lambda p: p.type not in ['consu', 'service']).update({'can_be_expensed': False})
