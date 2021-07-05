# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_to_purchase = fields.Boolean("Subcontract Service", help="If ticked, each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.")

    _sql_constraints = [
        ('service_to_purchase', "CHECK((type != 'service' AND service_to_purchase != true) or (type = 'service'))", 'Product that is not a service can not create RFQ.'),
    ]

    @api.constrains('service_to_purchase', 'seller_ids')
    def validate_service_to_purchase(self):
        if self.service_to_purchase and not self.seller_ids:
            raise ValidationError("Please define the vendor from whom you would like to purchase this service automatically.")

    @api.onchange('type')
    def _onchange_type(self):
        res = super(ProductTemplate, self)._onchange_type()
        if self.type != 'service':
            self.service_to_purchase = False
        return res

    @api.onchange('expense_policy')
    def _onchange_expense_policy(self):
        if self.expense_policy != 'no':
            self.service_to_purchase = False
