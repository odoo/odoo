# -*- coding: utf-8 -*-

from odoo.addons.account_taxcloud.models import taxcloud_request

class TaxCloudRequest(taxcloud_request.TaxCloudRequest):

    def set_order_items_detail(self, order):
        self.customer_id = order.partner_invoice_id.id
        self.cart_items = self.factory.ArrayOfCartItem()
        self.cart_items.CartItem = self._process_lines(order.order_line)
