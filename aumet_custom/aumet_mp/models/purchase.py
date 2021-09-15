# -*- coding: utf-8 -*-
import posixpath
from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[
        ('mp_sent', 'Sent to Marketplace')
    ])

    def action_added_to_cart(self):
        for po in self:
            if all(po.order_line.mapped('mp_added_to_cart')):
                po.state = 'mp_sent'


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_mp = fields.Boolean('Marketplace', default=False)
    mp_product_id = fields.Many2one('marketplace.product', string='MP Product',
                                    help='Matching product for this product in marketplace')
    mp_added_to_cart = fields.Boolean('Added to cart', default=False)

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line(product_id, product_qty, product_uom,
                                                                          company_id, supplier, po)
        if supplier:
            res['is_mp'] = supplier.is_mp
            res['mp_product_id'] = supplier.mp_product_id.id
        return res

    def add_message(self, resp):
        mp_url = posixpath.join(self.company_id.market_place_id.base_url, "web/cart/checkout")

        message = _('''
        {msg}: <ul>
            <li>Product: <a href={mp_url} target="_blank"><b>{product}</b></a></li>
            <li>Unit Price: {unit_price}</li>
            <li>Quantity: {quantity}</li>
            </ul>
        '''.format(
            mp_url=mp_url,
            msg=resp.get('message', 'Unknown message!'),
            product=self.mp_product_id.name,
            unit_price=self.mp_product_id.unit_price,
            quantity=self.product_qty))

        self.order_id.message_post(body=message)

    @api.model
    def create(self, values):
        pol = super(PurchaseOrderLine, self).create(values)
        if pol.is_mp and pol.company_id.is_mp:
            # Add this line into Aumet cart
            result, resp = pol.company_id.add_product_to_cart(pol)
            if result:
                pol.mp_added_to_cart = True
                pol.order_id.action_added_to_cart()
            pol.add_message(resp)
        return pol
