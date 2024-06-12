# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields):
        result = super(ProductTemplate, self).default_get(fields)
        if self.env.context.get('default_can_be_expensed'):
            result['supplier_taxes_id'] = False
        return result

    can_be_expensed = fields.Boolean(string="Can be Expensed", compute='_compute_can_be_expensed',
        store=True, readonly=False, help="Specify whether the product can be selected in an expense.")

    def _auto_init(self):
        if not column_exists(self.env.cr, "product_template", "can_be_expensed"):
            create_column(self.env.cr, "product_template", "can_be_expensed", "boolean")
            self.env.cr.execute(
                """
                UPDATE product_template
                SET can_be_expensed = false
                WHERE type NOT IN ('consu', 'service')
                """
            )
        return super()._auto_init()

    @api.depends('type')
    def _compute_can_be_expensed(self):
        self.filtered(lambda p: p.type not in ['consu', 'service']).update({'can_be_expensed': False})
