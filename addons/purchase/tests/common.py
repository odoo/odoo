# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestPurchase(TestStockCommon):

    def _create_make_procurement(self, product, product_qty):
        MakeProcurement = self.env['make.procurement']
        order_values = {
            'product_id': product.id,
            'qty': product_qty,
            'uom_id': self.uom_unit.id,
            'warehouse_id': self.warehouse_1.id,
            'date_planned': fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10))  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
        }
        return MakeProcurement.create(order_values)

    @classmethod
    def setUpClass(cls):
        super(TestPurchase, cls).setUpClass()

        cls.route_buy = cls.warehouse_1.buy_pull_id.route_id.id
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id.id

        # Update product_1 with type, route and Delivery Lead Time
        cls.product_1.write({
            'type': 'product',
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(0, 0, {'name': cls.partner_1.id, 'delay': 5})]})

        # Update product_2 with type, route and Delivery Lead Time
        cls.product_2.write({
            'type': 'product',
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(0, 0, {'name': cls.partner_1.id, 'delay': 2})]})
