from odoo import Command
from odoo.addons.stock.tests.test_mtso import TestStockMtso


class TestPurchaseMtso(TestStockMtso):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.route_buy = cls.warehouse_1.buy_pull_id.route_id.id
        cls.productA.write({
            'route_ids': [Command.link(cls.route_mtso.id), Command.link(cls.route_buy)],
            'seller_ids': [Command.create({
                'partner_id': cls.partner_1.id,
                'price': 10.0,
            })],
        })
        cls.productB.write({
            'route_ids': [Command.link(cls.route_mtso.id), Command.link(cls.route_buy)],
            'seller_ids': [Command.create({
                'partner_id': cls.partner_2.id,
                'price': 10.0,
            })],
        })
