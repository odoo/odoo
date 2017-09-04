# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestPurchase(TestStockCommon):

    def _create_make_procurement(self, product, product_qty, date_planned=False):
        ProcurementGroup = self.env['procurement.group']
        order_values = {
            'warehouse_id': self.warehouse_1,
            'date_planned': date_planned or fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10)),  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
            'group_id': self.env['procurement.group'],
        }
        return ProcurementGroup.run(product, product_qty, self.uom_unit, self.warehouse_1.lot_stock_id, product.name, '/', order_values)

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
