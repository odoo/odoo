from odoo import Command
from odoo.tests.common import tagged
from odoo.addons.account_avatax.tests.common import TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraStock(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/sales-tax-badge/"""

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.shipping_partner = cls.env["res.partner"].create({
            'name': "Shipping Partner",
            'street': "234 W 18th Ave",
            'city': "Columbus",
            'state_id': cls.env.ref("base.state_us_30").id,  # Ohio
            'country_id': cls.env.ref("base.us").id,
            'zip': "43210",
        })

        # Partner to use for the warehouse's address
        warehouse_address_partner = cls.env["res.partner"].create({
            'name': "Address for second warehouse",
            'street': "100 Ravine Lane NE",
            'city': "Bainbridge Island",
            'state_id': cls.env.ref("base.state_us_48").id,  # Washington
            'country_id': cls.env.ref("base.us").id,
            'zip': "98110",
        })
        # Warehouse with different address than the company's
        cls.warehouse_with_different_address = cls.env['stock.warehouse'].create({
            'name': "Warehouse #2",
            'partner_id': warehouse_address_partner.id,
            'code': "WH02"
        })
        # Warehouse with the same address as the company
        cls.warehouse_with_same_address = cls.env['stock.warehouse'].create({
            'name': "Warehouse #3",
            'partner_id': cls.env.user.company_id.partner_id.id,
            'code': "WH03"
        })

        return res

    def test_line_level_address_sale_order_warehouse(self):
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'partner_shipping_id': self.shipping_partner.id,
                'fiscal_position_id': self.fp_avatax.id,
                'date_order': '2021-01-01',
                'warehouse_id': self.warehouse_with_different_address.id,
                'order_line': [
                    (0, 0, {
                        'product_id': self.product.id,
                        'tax_id': None,
                        'price_unit': self.product.list_price,
                    }),
                ]
            })
            sale_order.button_external_tax_calculation()
            line_addresses = capture.val['json']['createTransactionModel']['lines'][0].get('addresses', False)
            self.assertEqual(line_addresses['shipFrom']['region'], 'WA', 'should ship from the sales order warehouse')
            self.assertEqual(line_addresses['shipTo']['region'], 'OH', 'should ship to the delivery address')
            capture.val = None

            sale_order.action_confirm()
            line_addresses = capture.val['json']['createTransactionModel']['lines'][0].get('addresses', False)
            self.assertEqual(line_addresses['shipFrom']['region'], 'WA', 'should ship from the sales order warehouse')
            self.assertEqual(line_addresses['shipTo']['region'], 'OH', 'should ship to the delivery address')
            capture.val = None

            invoice = sale_order._create_invoices()
            invoice.button_external_tax_calculation()
            line_addresses = capture.val['json']['createTransactionModel']['lines'][0].get('addresses', False)
            self.assertEqual(line_addresses['shipFrom']['region'], 'WA', 'should ship from the sales order warehouse')
            self.assertEqual(line_addresses['shipTo']['region'], 'OH', 'should ship to the delivery address')

    def test_line_level_address_with_different_warehouse_address(self):
        """Ensure that invoices created from a sale order with items shipped from a different address than the
           company's have the correct line level addresses and items shipped from the same address as the
           company have no line level addresses.
        """
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'partner_shipping_id': self.shipping_partner.id,
                'fiscal_position_id': self.fp_avatax.id,
                'date_order': '2021-01-01',
                'order_line': [
                    (0, 0, {
                        'product_id': self.product.id,
                        'tax_id': None,
                        'price_unit': self.product.list_price,
                    }),
                    (0, 0, {
                        'product_id': self.product_user.id,
                        'tax_id': None,
                        'price_unit': self.product_user.list_price,
                    }),
                    (0, 0, {
                        'product_id': self.product_accounting.id,
                        'tax_id': None,
                        'price_unit': self.product_accounting.list_price,
                    }),
                ]
            })
            sale_order.action_confirm()

            self.assertEqual(len(sale_order.picking_ids.move_ids), 3, "Three stock moves should be created from the sale order.")

            # Change the source location of the first move to a warehouse with different address and the source location
            # of the second move to a warehouse with the same address as the company's. Third move is unchanged.
            move01 = sale_order.picking_ids.move_ids[0]
            move01.location_id = self.warehouse_with_different_address.lot_stock_id
            move02 = sale_order.picking_ids.move_ids[1]
            move02.location_id = self.warehouse_with_same_address.lot_stock_id

            invoice = sale_order._create_invoices()
            invoice.button_external_tax_calculation()

        # Line 1
        line_addresses = capture.val['json']['createTransactionModel']['lines'][0].get('addresses', False)
        self.assertTrue(line_addresses, "Line level addresses should be created for different warehouse addresses.")
        self.assertEqual(line_addresses, {
            'shipFrom': {
                'city': 'Bainbridge Island',
                'country': 'US',
                'line1': '100 Ravine Lane NE',
                'postalCode': '98110',
                'region': 'WA'
            },
            'shipTo': {
                'city': 'Columbus',
                'country': 'US',
                'line1': '234 W 18th Ave',
                'postalCode': '43210',
                'region': 'OH'
            }}, "Line level address should have the correct shipForm and shipTo")
        # Line 2
        line_addresses = capture.val['json']['createTransactionModel']['lines'][1].get('addresses', False)
        self.assertFalse(line_addresses, "Line level addresses should not be created for a warehouse with the same address as the company.")
        # Line 3
        line_addresses = capture.val['json']['createTransactionModel']['lines'][2].get('addresses', False)
        self.assertFalse(line_addresses, "Line level addresses should not be created for a warehouse with the same address as the company.")

    def test_line_level_address_with_backorders(self):
        """Send line-level addresses even if a sale order line has multiple stock moves. As long as they're linked to a
        single warehouse address, it's ok to send.
        """
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'partner_shipping_id': self.shipping_partner.id,
                'fiscal_position_id': self.fp_avatax.id,
                'date_order': '2021-01-01',
                'warehouse_id': self.warehouse_with_different_address.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'tax_id': None,
                        'price_unit': self.product.list_price,
                        'product_uom_qty': 2,
                    }),
                ]
            })
            sale_order.action_confirm()
            sale_order.picking_ids.move_ids.quantity = 1  # do half

            # validate and create backorder
            res_dict = sale_order.picking_ids.button_validate()
            self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process()

            self.assertEqual(len(sale_order.picking_ids), 2, "There should be two pickings: the original one for qty 1 and the backorder for the remaining qty 1.")
            self.assertEqual(len(sale_order.order_line.move_ids), 2, "There should be two moves associated to this single order line, one for the original picking, the other for the backorder.")

            invoice = sale_order._create_invoices()
            invoice.button_external_tax_calculation()

        line_address = capture.val['json']['createTransactionModel']['lines'][0].get('addresses')
        self.assertTrue(line_address, "Send a line level address, even though two moves are associated to the line, they both refer to the same address.")
