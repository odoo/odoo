# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_to_purchase = fields.Boolean(
        "Subcontract Service", company_dependent=True, copy=False,
        help="If ticked, each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.")

    @api.constrains('service_to_purchase', 'seller_ids', 'type')
    def _check_service_to_purchase(self):
        for template in self:
            if template.service_to_purchase:
                if template.type != 'service':
                    raise ValidationError(_("Product that is not a service can not create RFQ."))
                template._check_vendor_for_service_to_purchase(template.seller_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('service_to_purchase'):
                self._check_vendor_for_service_to_purchase(vals.get('seller_ids'))
        return super().create(vals_list)

    def _check_vendor_for_service_to_purchase(self, sellers):
        if not sellers:
            raise ValidationError(_("Please define the vendor from whom you would like to purchase this service automatically."))

    @api.onchange('type', 'expense_policy')
    def _onchange_service_to_purchase(self):
        products_template = self.filtered(lambda p: p.type != 'service' or p.expense_policy != 'no')
        products_template.service_to_purchase = False
