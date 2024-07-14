# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class SendCloudShippingProduct(models.Model):

    _name = "sendcloud.shipping.product"
    _description = "Choose from the available sendcloud shipping products"

    name = fields.Char(string="Shipping Product", required=True, readonly=True)
    # sendcloud_code can be used as an id to guarantee the uniqueness of the record
    # howewer SendCloud doesn't allow it's use as a search parameter
    sendcloud_code = fields.Char(string="Sendcloud Product Identifier", required=True, readonly=True)
    carrier = fields.Char(string="Shipping Carrier", readonly=True)
    min_weight = fields.Integer(string="Minimum Weight", readonly=True)
    max_weight = fields.Integer(string="Maximum Weight", readonly=True)
    functionalities = fields.Json(string="Available Functionalities", readonly=True)  # dict with keys 'bool_func', 'detail_func', 'customizable'. customizable hold technical names, other ones humanized names
    can_customize_functionalities = fields.Boolean(compute='_compute_can_customize_functionalities', store=True)
    has_multicollo = fields.Boolean(compute='_compute_has_multicollo', store=True)

    @api.depends('functionalities')
    def _compute_can_customize_functionalities(self):
        self.can_customize_functionalities = False
        for sc_product in self:
            if sc_product.functionalities.get('customizable'):
                sc_product.can_customize_functionalities = True

    @api.depends('functionalities')
    def _compute_has_multicollo(self):
        self.has_multicollo = False
        for sc_product in self:
            if 'Multicollo' in sc_product.functionalities.get('bool_func', []):
                sc_product.has_multicollo = True
