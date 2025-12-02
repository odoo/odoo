# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import Command, fields
from odoo.addons.stock.tests.common import TestStockCommon
from odoo import tools


class PurchaseTestCommon(TestStockCommon):

    def _create_make_procurement(self, product, product_qty, date_planned=False, ref=False):
        StockRule = self.env['stock.rule']
        order_values = {
            'warehouse_id': self.warehouse_1,
            'action': 'pull_push',
            'date_planned': date_planned or fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=10)),  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
        }
        if ref:
            order_values['reference_ids'] = ref
        return StockRule.run([self.env['stock.rule'].Procurement(
            product, product_qty, self.uom_unit, self.warehouse_1.lot_stock_id,
            product.name, '/', self.env.company, order_values)
        ])

    @classmethod
    def setUpClass(cls):
        super(PurchaseTestCommon, cls).setUpClass()
        cls.route_mto.active = True

        cls.route_buy = cls.warehouse_1.buy_pull_id.route_id
        cls.categ_id = cls.env.ref('product.product_category_goods').id

        # Update product_1 with type, route and Delivery Lead Time
        cls.product_1.write({
            'is_storable': True,
            'route_ids': [Command.set([cls.route_buy.id, cls.route_mto.id])],
            'seller_ids': [Command.create({'partner_id': cls.partner_1.id, 'delay': 5})],
            'categ_id': cls.categ_id,
        })

        cls.t_shirt = cls.env['product.product'].create({
            'name': 'T-shirt',
            'description': 'Internal Notes',
            'route_ids': [Command.set([cls.route_buy.id, cls.route_mto.id])],
            'seller_ids': [Command.create({'partner_id': cls.partner_1.id, 'delay': 5})]
        })

        # Update product_2 with type, route and Delivery Lead Time
        cls.product_2.write({
            'is_storable': True,
            'route_ids': [Command.set([cls.route_buy.id, cls.route_mto.id])],
            'seller_ids': [Command.create({'partner_id': cls.partner_1.id, 'delay': 2})],
            'categ_id': cls.categ_id,
        })

        cls.res_users_purchase_user = cls.env['res.users'].create({
            'company_id': cls.env.ref('base.main_company').id,
            'name': "Purchase User",
            'login': "pu",
            'email': "purchaseuser@yourcompany.com",
            'group_ids': [Command.set([cls.env.ref('purchase.group_purchase_user').id])],
            })

        cls.fuzzy_drink = cls.env['product.product'].create({
            'name': 'Fuzzy Drink',
            'is_storable': True,
            'route_ids': [Command.set([cls.route_buy.id, cls.route_mto.id])],
            'seller_ids': [Command.create({
                'partner_id': cls.partner_1.id,
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'price': 1.0,
            }), Command.create({
                'partner_id': cls.partner_1.id,
                'product_uom_id': cls.env.ref('uom.product_uom_pack_6').id,
                'price': 5.0,
                'min_qty': 2,
            })]
        })
