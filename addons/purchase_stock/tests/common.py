# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.addons.stock.tests.common import TestStockCommon
from odoo import tools


class PurchaseTestCommon(TestStockCommon):

    def _create_make_procurement(self, product, product_qty, date_planned=False):
        ProcurementGroup = self.env['procurement.group']
        order_values = {
            'warehouse_id': self.warehouse_1,
            'action': 'pull_push',
            'date_planned': date_planned or fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=10)),  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
            'group_id': self.env['procurement.group'],
        }
        return ProcurementGroup.run([self.env['procurement.group'].Procurement(
            product, product_qty, self.uom_unit, self.warehouse_1.lot_stock_id,
            product.name, '/', self.stock_company, order_values)
        ])

    @classmethod
    def setUpClass(cls):
        super(PurchaseTestCommon, cls).setUpClass()
        cls.user_stock_user.groups_id += cls.env.ref('purchase.group_purchase_user')
        cls.user_stock_manager.groups_id += cls.env.ref('purchase.group_purchase_user')
        cls.env.ref('stock.route_warehouse0_mto').active = True

        cls.route_buy = cls.warehouse_1.buy_pull_id.route_id.id
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id.id
        cls.categ_id = cls.env.ref('product.product_category_goods').id

        # Update product_1 with type, route and Delivery Lead Time
        cls.product_1.write({
            'is_storable': True,
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(0, 0, {
                'partner_id': cls.partner.id,
                'delay': 5,
                'company_id': cls.stock_company.id,
            })],
            'categ_id': cls.categ_id,
        })

        cls.t_shirt = cls.env['product.product'].create({
            'name': 'T-shirt',
            'description': 'Internal Notes',
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(0, 0, {
                'partner_id': cls.partner.id,
                'delay': 5,
                'company_id': cls.stock_company.id,
            })],
        })

        # Update product_2 with type, route and Delivery Lead Time
        cls.product_2.write({
            'is_storable': True,
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(0, 0, {
                'partner_id': cls.partner.id,
                'delay': 2,
                'company_id': cls.stock_company.id,
            })],
            'categ_id': cls.categ_id,
        })

        cls.res_users_purchase_user = cls.env['res.users'].sudo().create({
            'company_id': cls.company.id,
            'name': "Purchase User",
            'login': "pu",
            'email': "purchaseuser@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('purchase.group_purchase_user').id])],
            })
