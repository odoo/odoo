# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_to_purchase = fields.Boolean("Purchase Automatically", help="If ticked, each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.")

    _sql_constraints = [
        ('service_to_purchase', "CHECK((type != 'service' AND service_to_purchase != true) or (type = 'service'))", 'Product that is not a service can not create RFQ.'),
    ]

    @api.onchange('type')
    def _onchange_product_type(self):
        if self.type != 'service':
            self.service_to_purchase = False

    @api.onchange('expense_policy')
    def _onchange_expense_policy(self):
        if self.expense_policy != 'no':
            self.service_to_purchase = False
