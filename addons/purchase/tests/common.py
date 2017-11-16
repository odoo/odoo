# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.addons.stock.tests.common2 import TestStockCommon
from odoo import tools
from odoo.modules.module import get_module_resource


class TestPurchase(TestStockCommon):

    def _create_product(self, uom_po_id=False, cost_method='real', price=0.0):
        return self.env['product.product'].create({
            'default_code': 'MYTEST',
            'name': 'Test Product',
            'type': 'product',
            'categ_id': self.categ_all_id,
            'list_price': 100.0,
            'standard_price': price,
            'uom_id': self.uom_kg_id,
            'uom_po_id': uom_po_id,
            'cost_method': cost_method,
            'valuation': 'real_time',
            'property_stock_account_input': self.ref('purchase.o_expense'),
            'property_stock_account_output': self.ref('purchase.o_income'),
            'description': 'FIFO Ice Cream can be mass-produced and thus is widely available in developed parts of the world. Ice cream can be purchased in large cartons (vats and squrounds) from supermarkets and grocery stores, in smaller quantities from ice cream shops, convenience stores, and milk bars, and in individual servings from small carts or vans at public events.',
        })

    def _create_make_procurement(self, product, product_qty, date_planned=False):
        ProcurementGroup = self.env['procurement.group']
        MakeProcurement = self.env['make.procurement']
        order_values = {
            'warehouse_id': self.warehouse_1,
            'date_planned': date_planned or fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10)),  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
            'group_id': self.env['procurement.group'],
        }
        return ProcurementGroup.run(product, product_qty, self.uom_unit, self.warehouse_1.lot_stock_id, product.name, '/', order_values)

    def _load(self, module, *args):
        tools.convert_file(self.cr, 'purchase',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test', self.registry._assertion_report)

    @classmethod
    def setUpClass(cls):
        super(TestPurchase, cls).setUpClass()

        # Usefull Models.
        cls.Product = cls.env['product.product']
        cls.PurchaseOrder = cls.env['purchase.order']
        cls.StockPicking = cls.env['stock.picking']
        cls.Move = cls.env['stock.move']
        cls.Procurement = cls.env['procurement.order']
        cls.StockTransfer = cls.env['stock.immediate.transfer']


        # Useful Reference.
        cls.uom_kg_id = cls.env.ref('product.product_uom_kgm').id
        cls.categ_all_id = cls.env.ref('product.product_category_1').id
        cls.stock_location_id = cls.env.ref('stock.stock_location_stock').id
        cls.customer_location_id = cls.env.ref('stock.stock_location_customers').id
        cls.pick_type_out_id = cls.env.ref('stock.picking_type_out').id
        cls.uom_gram_id = cls.env.ref('product.product_uom_gram').id
        cls.partner_id = cls.env.ref('base.res_partner_3').id

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

        cls.res_users_purchase_user = cls.env['res.users'].create({
            'company_id': cls.env.ref('base.main_company').id,
            'name': "Purchase User",
            'login': "pu",
            'email': "purchaseuser@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('purchase.group_purchase_user').id])],
            })
