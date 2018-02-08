# -*- coding: utf-8 -*-

from odoo.tests import common
from odoo.tools import float_compare


@common.tagged('post_install', '-at_install')
class TestDeliveryCost(common.TransactionCase):

    def setUp(self):
        super(TestDeliveryCost, self).setUp()
        self.SaleOrder = self.env['sale.order']
        self.SaleOrderLine = self.env['sale.order.line']
        self.AccountAccount = self.env['account.account']
        self.SaleConfigSetting = self.env['res.config.settings']
        self.Product = self.env['product.product']

        self.partner_18 = self.env.ref('base.res_partner_18')
        self.pricelist = self.env.ref('product.list0')
        self.product_4 = self.env.ref('product.product_product_4')
        self.product_uom_unit = self.env.ref('product.product_uom_unit')
        self.normal_delivery = self.env.ref('delivery.normal_delivery_carrier')
        self.partner_4 = self.env.ref('base.res_partner_4')
        self.partner_address_13 = self.env.ref('base.res_partner_address_13')
        self.product_uom_hour = self.env.ref('product.product_uom_hour')
        self.account_data = self.env.ref('account.data_account_type_revenue')
        self.account_tag_operating = self.env.ref('account.account_tag_operating')
        self.product_2 = self.env.ref('product.product_product_2')
        self.product_category = self.env.ref('product.product_category_all')
        self.free_delivery = self.env.ref('delivery.free_delivery_carrier')
        # as the tests hereunder assume all the prices in USD, we must ensure
        # that the company actually uses USD
        self.env.user.company_id.write({'currency_id': self.env.ref('base.USD').id})

    def test_00_delivery_cost(self):
        # In order to test Carrier Cost
        # Create sales order with Normal Delivery Charges

        self.sale_normal_delivery_charges = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 1,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
            'carrier_id': self.normal_delivery.id
        })
        # I add delivery cost in Sales order

        self.a_sale = self.AccountAccount.create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'user_type_id': self.account_data.id,
            'tag_ids': [(6, 0, {
                self.account_tag_operating.id
            })]
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

        # I add delivery cost in Sales order
        self.sale_normal_delivery_charges.get_delivery_price()
        self.sale_normal_delivery_charges.set_delivery_line()

        # I check sales order after added delivery cost

        line = self.SaleOrderLine.search([('order_id', '=', self.sale_normal_delivery_charges.id),
            ('product_id', '=', self.sale_normal_delivery_charges.carrier_id.product_id.id)])
        self.assertEqual(len(line), 1, "Delivery cost is not Added")

        self.assertEqual(float_compare(line.price_subtotal, 10.0, precision_digits=2), 0,
            "Delivery cost is not correspond.")

        # I confirm the sales order

        self.sale_normal_delivery_charges.action_confirm()

        # Create one more sales order with Free Delivery Charges

        self.delivery_sale_order_cost = self.SaleOrder.create({
            'partner_id': self.partner_4.id,
            'partner_invoice_id': self.partner_address_13.id,
            'partner_shipping_id': self.partner_address_13.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [(0, 0, {
                'name': 'Service on demand',
                'product_id': self.product_consultant.id,
                'product_uom_qty': 24,
                'product_uom': self.product_uom_hour.id,
                'price_unit': 75.00,
            }), (0, 0, {
                'name': 'On Site Assistance',
                'product_id': self.product_2.id,
                'product_uom_qty': 30,
                'product_uom': self.product_uom_hour.id,
                'price_unit': 38.25,
            })],
            'carrier_id': self.free_delivery.id
        })

        # I add free delivery cost in Sales order
        self.delivery_sale_order_cost.get_delivery_price()
        self.delivery_sale_order_cost.set_delivery_line()

        # I check sales order after adding delivery cost
        line = self.SaleOrderLine.search([('order_id', '=', self.delivery_sale_order_cost.id),
            ('product_id', '=', self.delivery_sale_order_cost.carrier_id.product_id.id)])

        self.assertEqual(len(line), 1, "Delivery cost is not Added")
        self.assertEqual(float_compare(line.price_subtotal, 0, precision_digits=2), 0,
            "Delivery cost is not correspond.")

        # I set default delivery policy

        self.default_delivery_policy = self.SaleConfigSetting.create({})

        self.default_delivery_policy.execute()
