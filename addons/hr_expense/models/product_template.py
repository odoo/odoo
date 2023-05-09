# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    @api.depends('type')
    def _compute_can_be_expensed(self):
        self.filtered(lambda p: p.type not in ['consu', 'service']).update({'can_be_expensed': False})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_sale_expense_products(self):
        product_data = [
            self.env.ref('hr_expense.food_expense_product', False),
            self.env.ref('hr_expense.mileage_expense_product', False),
            self.env.ref('hr_expense.accomodation_expense_product', False),
            self.env.ref('hr_expense.allowance_expense_product', False)
        ]
        for product in self.filtered(lambda p: p.product_variant_ids in product_data):
            raise UserError(_(
                "You cannot delete %(name)s as it is used in 'Sales Expense'."
                "Please archive it instead.",
                name=product.name
            ))
