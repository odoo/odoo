# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestStockDropshippingCommon(common.TransactionCase):

    def setUp(self):
        super(TestStockDropshippingCommon, self).setUp()

        self.ProcurementGroup = self.env['procurement.group']
        self.ProcurementOrder = self.env['procurement.order']
        self.PurchaseOrder = self.env['purchase.order']
        self.Product = self.env['product.product']
        self.ProductCategory = self.env['product.category']
        self.SaleOrder = self.env['sale.order']
        self.StockMove = self.env['stock.move']
        self.StockQuant = self.env['stock.quant']
        self.StockPicking = self.env['stock.picking']
        self.StockWarehouse = self.env['stock.warehouse']
        self.ResPartner = self.env['res.partner']
        self.Account = self.env['account.account']
        self.AccountJournal = self.env['account.journal']
        # Model Data
        self.product_category1_id = self.ref('product.product_category_1')
        self.stock_location_customer_id = self.ref('stock.stock_location_customers')
        self.pricelist0 = self.ref('product.list0')
        self.warehouse0 = self.env.ref('stock.warehouse0')
        self.partner_cus_a_id = self.ref('base.res_partner_3')
        self.partner_cus_b_id = self.ref('base.res_partner_4')
        self.partner_sup_id = self.ref('base.res_partner_2')
        self.product_uom_unit_id = self.ref('product.product_uom_unit')
        self.product_uom_dozen_id = self.ref('product.product_uom_dozen')
        self.product_uom_kgm_id = self.ref('product.product_uom_kgm')
        self.account_payment_term_id = self.ref('account.account_payment_term')
        self.route_drop_shipping_id = self.ref('stock_dropshipping.route_drop_shipping')
        # Create a warehouse with pick-pack-ship and receipt in 2 steps
        self.wh_pps = self.StockWarehouse.create({
              'name': 'WareHouse PickPackShip', 'code': 'whpps',
              'reception_steps': 'two_steps', 'delivery_steps': 'pick_pack_ship'})
        # Create Account
        self.o_income = self.Account.create({
             'name': 'Opening Income', 'code': 'X1016',
             'user_type_id': self.env['account.account.type'].create({'name': 'Other Income', 'type': 'other'}).id})
        self.o_expense = self.Account.create({
             'name': 'Opening Expense', 'code': 'X1114',
             'user_type_id': self.env['account.account.type'].create({'name': 'Other Expenses', 'type': 'other'}).id})
        self.o_valuation = self.Account.create({
             'name': 'Stock Valuation', 'code': 'X1115',
             'user_type_id': self.env['account.account.type'].create({'name': 'Stock Valuation', 'type': 'other'}).id})
        self.default_account = self.Account.create({
             'name': "Purchased Stocks", 'code': "X1101", 'reconcile': True,
             'user_type_id': self.env['account.account.type'].create({'name': 'Expenses', 'type': 'other'}).id})
        self.stock_journal = self.AccountJournal.create({
             'name': 'Stock - Test', 'code': 'STXJ', 'type': 'general',
             'default_debit_account_id': self.default_account.id, 'default_credit_account_id': self.default_account.id})
