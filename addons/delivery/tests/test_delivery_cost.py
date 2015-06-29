# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common
from openerp.tools import float_compare


class TestDeliveryCost(common.TransactionCase):

    def setUp(self):
        super(TestDeliveryCost, self).setUp()
        self.SaleOrder = self.env['sale.order']
        self.SaleOrderLine = self.env['sale.order.line']
        self.AccountJournal = self.env['account.journal']
        self.AccountAccount = self.env['account.account']
        self.StockInvoiceOnshipping = self.env['stock.invoice.onshipping']
        self.SaleConfigSetting = self.env['sale.config.settings']
        self.Product = self.env['product.product']

        self.partner_18 = self.env.ref('base.res_partner_18')
        self.pricelist = self.env.ref('product.list0')
        self.product_4 = self.env.ref('product.product_product_4')
        self.product_uom_unit = self.env.ref('product.product_uom_unit')
        self.normal_delivery = self.env.ref('delivery.normal_delivery_carrier')
        self.product_delivery = self.env.ref('delivery.product_product_delivery')
        self.partner_7 = self.env.ref('base.res_partner_7')
        self.partner_address_13 = self.env.ref('base.res_partner_address_13')
        self.product_uom_hour = self.env.ref('product.product_uom_hour')
        self.analytic_course = self.env.ref('analytic.cose_journal_sale')
        self.account_data = self.env.ref('account.data_account_type_revenue')
        self.account_tag_operating = self.env.ref('account.account_tag_operating')
        self.product_2 = self.env.ref('product.product_product_2')
        self.product_category = self.env.ref('product.product_category_all')
        self.free_delivery = self.env.ref('delivery.free_delivery_carrier')

    def test_00_delivery_cost(self):
        # In order to test Carrier Cost,
        # Create sale order with Normal Delivery Charges

        self.sale_normal_delivery_charges = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist.id,
            'order_policy': 'picking',
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 1,
                'product_uos_qty': 1,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
            'carrier_id': self.normal_delivery.id
        })
        # I add delivery cost in Sale order.

        self.a_sale = self.AccountAccount.create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'user_type_id': self.account_data.id,
            'tag_ids': [(6, 0, {
                self.account_tag_operating.id
            })]
        })

        self.sales_journal = self.AccountJournal.create({
            'name': 'Customer Invoices - Test',
            'code': 'TINV',
            'type': 'sale',
            'default_credit_account_id': self.a_sale.id,
            'default_debit_account_id': self.a_sale.id,
            'analytic_journal_id': self.analytic_course.id,
            'refund_sequence': True
        })

        self.product_consultant = self.Product.create({
            'sale_ok': True,
            'list_price': 75.0,
            'standard_price': 30.0,
            'uom_id': self.product_uom_hour.id,
            'uom_po_id': self.product_uom_hour.id,
            'name': 'Service',
            'categ_id': self.product_category.id,
            'type': 'service'
        })

        #I add delivery cost in Sale order.
        self.SaleOrder.browse(self.sale_normal_delivery_charges.id).delivery_set()

        #I check sale order after added delivery cost.

        line_ids = self.SaleOrderLine.search([('order_id', '=', self.sale_normal_delivery_charges.id),
            ('product_id', '=', self.product_delivery.id)])
        self.assertEqual(len(line_ids), 1, "Delivery cost is not Added")

        line_data = self.SaleOrderLine.browse(line_ids.id)
        self.assertEqual(float_compare(line_data.price_subtotal, 10, precision_digits=2), 0,
            "Delivey cost is not correspond.")

        #I confirm the sale order.

        self.sale_normal_delivery_charges.signal_workflow('order_confirm')

        #I create Invoice from shipment.

        sale_order = self.SaleOrder.browse(self.sale_normal_delivery_charges.id)
        ship_ids = [x.id for x in sale_order.picking_ids]

        context = {
            'journal_id': self.sales_journal.id,
            'active_ids': ship_ids,
            'active_id': ship_ids[0],
            'active_model': 'stock.picking'
        }
        wiz_id = self.StockInvoiceOnshipping.with_context(context).create({})
        wiz_id.with_context(context).create_invoice()

        # Create one more sale order with Free Delivery Charges

        self.delivery_sale_order_cost = self.SaleOrder.create({
            'partner_id': self.partner_7.id,
            'partner_invoice_id': self.partner_address_13.id,
            'partner_shipping_id': self.partner_address_13.id,
            'pricelist_id': self.pricelist.id,
            'order_policy': 'manual',
            'order_line': [(0, 0, {
                'name': 'Service on demand',
                'product_id': self.product_consultant.id,
                'product_uom_qty': 24,
                'product_uos_qty': 24,
                'product_uom': self.product_uom_hour.id,
                'price_unit': 75.00,
            }), (0, 0, {
                'name': 'On Site Assistance',
                'product_id': self.product_2.id,
                'product_uom_qty': 30,
                'product_uos_qty': 30,
                'product_uom': self.product_uom_hour.id,
                'price_unit': 38.25,
            })],
            'carrier_id': self.free_delivery.id
        })

        # I add free delivery cost in Sale order.
        self.SaleOrder.browse(self.delivery_sale_order_cost.id).delivery_set()

        # I check sale order after added delivery cost.
        line_ids = self.SaleOrderLine.search([('order_id', '=', self.delivery_sale_order_cost.id),
            ('product_id', '=', self.product_delivery.id)])

        self.assertEqual(len(line_ids), 1, "Delivery cost is not Added")
        line_data = self.SaleOrderLine.browse(line_ids.id)
        self.assertEqual(float_compare(line_data.price_subtotal, 0, precision_digits=2), 0,
            "Delivey cost is not correspond.")

        # I set default delivery policy.

        self.default_delivery_policy = self.SaleConfigSetting.create({})

        self.default_delivery_policy.execute()
