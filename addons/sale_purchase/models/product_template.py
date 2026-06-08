# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(selection_add=[
        ('subcontract', 'Subcontracting RFQ')
    ], ondelete={'subcontract': 'set default'})

    @api.depends('service_tracking')
    def _compute_purchase_ok(self):
        super()._compute_purchase_ok()
        self.filtered(lambda t: t.service_tracking == 'subcontract' and not t.purchase_ok).purchase_ok = True

    @api.depends('purchase_ok', 'reinvoice_policy')
    def _compute_service_tracking(self):
        super()._compute_service_tracking()
        self.filtered(lambda t: t.service_tracking == 'subcontract' and (not t.purchase_ok or t.reinvoice_policy != 'no')).service_tracking = 'no'

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + ['subcontract']

    @api.model
    def _get_product_types_allow_zero_price(self):
        return super()._get_product_types_allow_zero_price() + ['subcontract']

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        for template in templates.filtered(lambda t: t.service_tracking == 'subcontract'):
            template._check_vendor_for_service_tracking_subcontract(template.seller_ids)
        return templates

    def write(self, vals):
        res = super().write(vals)
        for template in self.filtered(lambda t: t.service_tracking == 'subcontract'):
            template._check_vendor_for_service_tracking_subcontract(template.seller_ids)
        return res

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'subcontract':
            return self.env._("Each time you sell this product through a SO, a RfQ is automatically created to buy the product. Tip: don't forget to set a vendor on the product.")
        return super()._prepare_service_tracking_tooltip()

    def _check_vendor_for_service_tracking_subcontract(self, sellers):
        if not sellers:
            raise ValidationError(self.env._("Please define the vendor from whom you would like to purchase this service automatically."))
