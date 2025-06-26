from datetime import datetime, timedelta
from odoo import Command
from odoo.tests import common, Form, tagged

@tagged('post_install', '-at_install')
class TestWarnUnwantedReplenish(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')

        # Create a vendor (& suppliers) and a customer
        cls.vendor = cls.env['res.partner'].create(dict(name='Vendor'))
        cls.customer = cls.env['res.partner'].create(dict(name='Customer'))

        cls.supplier_A = cls.env['product.supplierinfo'].create({
            'partner_id' : cls.vendor.id,
            'min_qty' : 0.0,
            'price' : 10.0,
            'delay' : 0
        })

        cls.supplier_B = cls.env['product.supplierinfo'].create({
            'partner_id' : cls.vendor.id,
            'min_qty' : 0.0,
            'price' : 12.0,
            'delay' : 0
        })

        # Create a "A" and a "B" Product :
        # No Stock
        # Partner/Customer Lead Time = 0
        # Manual reordering 0 0

        cls.product_A = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'purchase_method': 'purchase',
            'invoice_policy': 'delivery',
            'standard_price': 5.0,
            'list_price': 10.0,
            'seller_ids': [Command.link(cls.supplier_A.id)],
            'route_ids': [Command.link(cls.buy_route.id)],
            'sale_delay' : 0,
        })

        cls.product_B = cls.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'purchase_method': 'purchase',
            'invoice_policy': 'delivery',
            'standard_price': 6.0,
            'list_price': 12.0,
            'seller_ids': [Command.link(cls.supplier_B.id)],
            'route_ids': [Command.link(cls.buy_route.id)],
            'sale_delay': 0,
        })


        orderpoint_form = Form(cls.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = cls.product_A
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 0.0
        cls.orderpoint_A = orderpoint_form.save()
        cls.orderpoint_A.trigger = 'manual'

        orderpoint_form = Form(cls.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = cls.product_B
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 0.0
        cls.orderpoint_B = orderpoint_form.save()
        cls.orderpoint_B.trigger = 'manual'

        # Create Sales
        # For A and for B
        # Delivered today
        # Confirm SO

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product_A.id,
                    'product_uom_qty': 10,
                }),
                Command.create({
                    'product_id': cls.product_B.id,
                    'product_uom_qty': 10,
                }),
            ],
        })

        cls.sale_order.action_confirm()

        # Create PO for Product A
        # Confirm PO with date planned : TODAY
        # Incoming Picking : reschedule in one week

        cls.po_A = cls.env['purchase.order'].create({
            'partner_id': cls.vendor.id,
            'order_line': [
                Command.create({
                    'name': cls.product_A.name,
                    'product_id': cls.product_A.id,
                    'product_qty': 10.0,
                    'price_unit': 10.0,
                    'date_planned': datetime.today(),
                })],
        })

        cls.po_A.button_confirm()

        cls.picking_A = cls.po_A.picking_ids[0]
        cls.picking_A.scheduled_date = (datetime.today() + timedelta(days=10))

    def test_01_pre_updateA_post(self):
        """
        TEST 1
          Replenishment ->
            Product A
                unwanted_replenish SHALL be TRUE
            Product B
                unwanted_replenish SHALL be FALSE
            Product A
                Modify Visible Days past 1 Week -> unwanted_replenish SHALL be FALSE
        """
        self.assertTrue(self.orderpoint_A.unwanted_replenish, 'Orderpoint A not set to unwanted_replenish')
        self.assertFalse(self.orderpoint_B.unwanted_replenish, 'Orderpoint B is set to unwanted_replenish')
        #Update Orderpoint A
        self.orderpoint_A.visibility_days = 10
        self.assertFalse(self.orderpoint_A.unwanted_replenish, 'Orderpoint A shall not be set to unwanted_replenish')
