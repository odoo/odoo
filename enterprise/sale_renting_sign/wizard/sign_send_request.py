# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SignSendRequest(models.TransientModel):
    _inherit = "sign.send.request"

    sale_order_id = fields.Many2one("sale.order", string="Sales Order")

    def create_request(self):
        sign_request = super(SignSendRequest, self).create_request()
        if self.sale_order_id:
            sign_request.reference_doc = f"sale.order,{self.sale_order_id.id}"
        return sign_request
