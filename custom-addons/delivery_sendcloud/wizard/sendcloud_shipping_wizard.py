# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SendCloudShippingWizard(models.TransientModel):

    _name = "sendcloud.shipping.wizard"
    _description = "Choose from the available sendcloud shipping methods"

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery")

    shipping_products = fields.Json('Shipping Products')
    return_products = fields.Json('Return Products')

    # Using a Json rather than 2 Char fields allow us to work on reference from owl,
    # such allowing update of value on the same object client-side and server-side
    sendcloud_products_code = fields.Json("Active Products Code")

    def action_validate(self):
        active_shipping_product = next((p for p in self.shipping_products if p['code'] == self.sendcloud_products_code['shipping']), self.shipping_products[0])
        active_return_product = next((p for p in self.return_products if p['code'] and p['code'] == self.sendcloud_products_code['return']), False)
        self.carrier_id._set_sendcloud_products(active_shipping_product, active_return_product)
