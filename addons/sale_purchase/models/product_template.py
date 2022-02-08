# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_to_purchase = fields.Boolean(
        "Subcontract Service",
        compute='_compute_service_to_purchase', store=True, readonly=False,
        help="If ticked, each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.")

    _sql_constraints = [
        ('service_to_purchase', "CHECK((type != 'service' AND service_to_purchase != true) or (type = 'service'))", 'Product that is not a service can not create RFQ.'),
    ]

    @api.constrains('service_to_purchase', 'seller_ids')
    def _check_service_to_purchase(self):
        for template in self:
            if template.service_to_purchase and not template.seller_ids:
                raise ValidationError(_(
                    "Please define the vendor from whom you would like to purchase this service automatically."))

    @api.depends('type', 'expense_policy')
    def _compute_service_to_purchase(self):
        for template in self:
            if template.type != 'service' or template.expense_policy != 'no':
                template.service_to_purchase = False
