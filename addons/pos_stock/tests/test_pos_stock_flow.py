from freezegun import freeze_time

from odoo import fields
from odoo.fields import Command
from odoo.addons.pos_stock.tests.common import CommonPosStockTest


class TestPosStockFlow(CommonPosStockTest):

    def test_order_to_picking(self):
        """
            In order to test the Point of Sale in module, I will do three orders
            from the sale to the payment, invoicing + picking, but will only
            check the picking consistency in the end.

            TODO: Check the negative picking after changing the picking relation
            to One2many (also for a mixed use case), check the quantity, the
            locations and return picking logic
        """
        order_1, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_jcb.id,
                'pricelist_id': self.partner_jcb.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 30},
            ],
        })
        order_2, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_lowe.id,
                'pricelist_id': self.partner_lowe.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 30},
            ],
        })
        order_3, order_refund_3 = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_vlst.id,
                'pricelist_id': self.partner_vlst.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 30},
            ],
            'refund_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': -30},
            ],
        })

        self.assertEqual(order_1.state, 'paid', 'Order should be in paid state.')
        self.assertEqual(order_1.picking_ids[0].state, 'done')
        self.assertEqual(order_1.picking_ids[0].move_ids.mapped('state'), ['done', 'done'])
        self.assertEqual(order_2.state, 'paid', 'Order should be in paid state.')
        self.assertEqual(order_2.picking_ids[0].state, 'done')
        self.assertEqual(order_2.picking_ids[0].move_ids.mapped('state'), ['done', 'done'])
        self.assertEqual(order_3.state, 'paid', 'Order should be in paid state.')
        self.assertEqual(order_3.picking_ids[0].state, 'done')
        self.assertEqual(order_3.picking_ids[0].move_ids.mapped('state'), ['done', 'done'])

        order_refund_3.action_pos_order_invoice()
        legal_documents = order_refund_3.account_move._get_invoice_legal_documents('pdf', allow_fallback=True)
        self.assertEqual(len(legal_documents), 1)
        invoice_pdf_content = str(legal_documents[0]['content'])
        self.assertTrue("using Cash" in invoice_pdf_content)
        self.assertEqual(order_refund_3.picking_count, 1)
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

    def test_order_to_picking02(self):
        """
            This test is similar to test_order_to_picking except that this time,
            there are two products:
                - One tracked by lot (ten_dollars_with_10_incl)
                - One untracked (twenty_dollars_with_15_incl)
                - Both are in a sublocation of the main warehouse
        """
        wh_location = self.company_data['default_warehouse'].lot_stock_id
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': wh_location.id,
        })
        self.ten_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'lot',
            'is_storable': True,
        })
        self.twenty_dollars_with_15_incl.product_variant_id.write({
            'tracking': 'none',
            'is_storable': True,
        })
        lot = self.env['stock.lot'].create({
            'name': 'SuperLot',
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
        })

        quantity_1 = self.env['stock.quant']._update_available_quantity(
            self.ten_dollars_with_10_incl.product_variant_id, shelf1_location, 2, lot_id=lot)
        quantity_2 = self.env['stock.quant']._update_available_quantity(
            self.twenty_dollars_with_15_incl.product_variant_id, shelf1_location, 2)

        self.assertEqual(quantity_1[0], 2)
        self.assertEqual(quantity_2[0], 2)
        self.pos_config_usd.open_ui()
        self.pos_config_usd.current_session_id.update_stock_at_closing = False
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_manv.id,
                'pricelist_id': self.partner_manv.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 30},
            ],
        })

        self.assertEqual(order.state, 'paid')
        tracked_line = self.env['stock.move.line'].search(
            [('product_id', '=', self.ten_dollars_with_10_incl.product_variant_id.id)])
        untracked_line = order.picking_ids.move_line_ids - tracked_line
        self.assertEqual(tracked_line.lot_id, lot)
        self.assertFalse(untracked_line.lot_id)
        self.assertEqual(tracked_line.location_id, shelf1_location)
        self.assertEqual(untracked_line.location_id, shelf1_location)

        res = order.action_pos_order_invoice()
        invoice_test = self.env['account.move'].browse(res['res_id'])
        self.assertEqual(invoice_test.ref, invoice_test.pos_order_ids.display_name)

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

    def test_order_to_invoice_uses_correct_shipping_address(self):
        """
        Test that invoice created from POS uses the correct shipping address
        same as selected in the POS order.
        """
        _, delivery2 = self.env["res.partner"].create([{
                'name': f"Delivery Address {i + 1}",
                'type': 'delivery',
                'parent_id': self.partner.id,
            } for i in range(2)]
        )

        self.pos_config_eur.open_ui()
        current_session = self.pos_config_eur.current_session_id
        untax, tax = self.compute_tax(self.product, 100, 1)

        pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': delivery2.id,
            'pricelist_id': self.partner.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product.id,
                'price_unit': 100,
                'qty': 1.0,
                'tax_ids': [(6, 0, self.product.taxes_id.ids)],
                'price_subtotal': untax,
                'price_subtotal_incl': untax + tax,
            })],
            'amount_tax': tax,
            'amount_total': untax + tax,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })

        pos_order.action_pos_order_invoice()
        invoice = pos_order.account_move

        self.assertEqual(
            invoice.partner_shipping_id.id,
            delivery2.id,
            "The shipping address should be 'Delivery Address 2' as selected in the POS order."
        )

    def test_order_multi_step_route(self):
        """
            Test that orders in sessions with "Ship Later" enabled and
            "Specific Route" set to a multi-step (2/3) route can be validated.
            This config implies multiple picking types and multiple move_lines.
        """
        self.ten_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'lot',
            'is_storable': True,
        })
        self.twenty_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'lot',
            'is_storable': True,
        })
        twenty_dollars_lot = self.env['stock.lot'].create({
            'name': '80085',
            'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id,
        })
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        stock_quantity = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'lot_id': twenty_dollars_lot.id
        })
        stock_quantity.action_apply_inventory()
        warehouse_id = self.company_data['default_warehouse']
        warehouse_id.delivery_steps = 'pick_ship'

        self.pos_config_usd.write({
            'ship_later': True,
            'warehouse_id': warehouse_id.id,
            'route_id': warehouse_id.route_ids[-1].id,
        })

        self.pos_config_usd.open_ui()
        self.pos_config_usd.current_session_id.update_stock_at_closing = False
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'shipping_date': fields.Date.today(),
                'partner_id': self.partner_mobt.id,
                'pricelist_id': self.partner_mobt.property_product_pricelist.id,
            },
            'line_data': [
                {
                    'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
                    'pack_lot_ids': [[0, 0, {'lot_name': '80085'}]],
                },
                {
                    'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id,
                    'pack_lot_ids': [[0, 0, {'lot_name': '80085'}]],
                },
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 30},
            ],
        })
        picking_mls_no_stock = order.picking_ids.move_line_ids.filtered(
            lambda l: l.product_id.id == self.ten_dollars_with_10_incl.product_variant_id.id)
        picking_mls_stock = order.picking_ids.move_line_ids.filtered(
            lambda l: l.product_id.id == self.twenty_dollars_with_10_incl.product_variant_id.id)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(len(picking_mls_no_stock), 0)
        self.assertEqual(len(picking_mls_stock), 1)
        self.assertEqual(len(order.picking_ids.picking_type_id), 1)

    def test_sale_order_postponed_invoicing_anglosaxon(self):
        """ Test the flow of creating an invoice later, after the POS session has been closed and everything has been processed
        in the case of anglo-saxon accounting.
        """
        self.env.company.anglo_saxon_accounting = True
        self.env.company.point_of_sale_update_stock_quantities = 'closing'
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 20.0},
            ],
        })
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        with freeze_time('2020-01-03'):
            order.partner_id = self.partner_stva.id
            order.action_pos_order_invoice()

        picking_ids = order.session_id.picking_ids
        self.assertEqual(sum(picking_ids.move_line_ids.mapped('quantity')), 1)

    def test_tracked_product_with_owner(self):
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.ten_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'serial',
            'is_storable': True,
        })
        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
        })
        self.env['stock.quant']._update_available_quantity(
            self.ten_dollars_with_10_incl.product_variant_id,
            self.stock_location,
            1, lot_id=lot1, owner_id=self.partner_adgu)

        # create pos order with the two SN created before
        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_adgu.id,
                'pricelist_id': self.pos_config_usd.pricelist_id.id,
            },
            'line_data': [
                {
                    'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
                    'pack_lot_ids': [[0, 0, {'lot_name': lot1.name}]],
                },
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
            ],
        })
        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.picking_ids.move_line_ids.owner_id.id, self.partner_adgu.id)

    def test_multi_exp_account_real_time(self):
        self.real_time_categ = self.env['product.category'].create({
            'name': 'test category',
            'parent_id': False,
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        self.account1 = self.env['account.account'].create({
            'name': 'Account 1',
            'code': 'AC1',
            'reconcile': True,
            'account_type': 'expense',
        })
        self.account2 = self.env['account.account'].create({
            'name': 'Account 2',
            'code': 'AC2',
            'reconcile': True,
            'account_type': 'expense',
        })
        self.ten_dollars_with_15_incl.write({
            'is_storable': True,
            'categ_id': self.real_time_categ.id,
            'property_account_expense_id': self.account1.id,
            'property_account_income_id': self.account1.id,
        })
        self.twenty_dollars_with_15_incl.write({
            'is_storable': True,
            'categ_id': self.real_time_categ.id,
            'property_account_expense_id': self.account2.id,
            'property_account_income_id': self.account2.id,
        })
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'pricelist_id': self.pos_config_usd.pricelist_id.id,
                'partner_id': self.partner_adgu.id,
                'shipping_date': fields.Date.today(),
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_15_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 30},
            ],
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        order.picking_ids._action_done()
        self.assertEqual(len(order.picking_ids.move_ids), 2)

    def test_order_different_lots(self):
        self.pos_config_usd.open_ui()
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.ten_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'lot',
            'is_storable': True,
        })

        lot_1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
        })

        stock_quant_1 = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
            'inventory_quantity': 5,
            'location_id': self.stock_location.id,
            'lot_id': lot_1.id
        })
        stock_quant_1.action_apply_inventory()
        stock_quant_2 = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
            'inventory_quantity': 5,
            'location_id': self.stock_location.id,
            'lot_id': lot_2.id
        })
        stock_quant_2.action_apply_inventory()
        self.assertEqual(stock_quant_1.quantity, 5)
        self.assertEqual(stock_quant_2.quantity, 5)
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_adgu.id,
                'pricelist_id': self.pos_config_usd.pricelist_id.id,
            },
            'line_data': [{
                    'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
                    'pack_lot_ids': [[0, 0, {'lot_name': '1001'}]],
                    'qty': 1,
                }, {
                    'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
                    'pack_lot_ids': [[0, 0, {'lot_name': '1002'}]],
                    'qty': 2,
                },
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 30},
            ],
        })
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertEqual(order.state, 'done')

        # Quantity decreased because from the same location
        self.assertEqual(stock_quant_1.quantity, 4)
        self.assertEqual(stock_quant_2.quantity, 3)

    def test_order_unexisting_lots(self):
        self.ten_dollars_with_10_incl.product_variant_id.write({
            'tracking': 'lot',
            'is_storable': True,
        })

        order, _ = self.create_backend_pos_order({
            'line_data': [{
                'product_id': self.ten_dollars_with_10_incl.product_variant_id.id,
                'pack_lot_ids': [[0, 0, {'lot_name': '1001'}]],
            }],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
            ],
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        order_lot_id = order.picking_ids.move_line_ids.lot_id
        self.assertEqual(order_lot_id.name, '1001')
        self.assertTrue(all(
            quant.lot_id == order_lot_id
            for quant in self.env['stock.quant'].search([
                ('product_id', '=', self.ten_dollars_with_10_incl.product_variant_id.id)
            ])
        ))

    def test_reordering_rules_triggered_closing_pos(self):
        if self.env['ir.module.module']._get('purchase').state != 'installed':
            self.skipTest("Purchase module is required for this test to run")

        self.env['stock.route'].search([('name', '=', 'Buy')]).warehouse_ids = self.env['stock.warehouse'].search([])
        self.ten_dollars_with_15_incl.write({
            'seller_ids': [Command.create({
                'partner_id': self.partner_stva.id,
                'min_qty': 1.0,
                'price': 10.0,
            })]
        })

        self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.ten_dollars_with_15_incl.product_variant_id.id,
            'location_id': self.pos_config_usd.picking_type_id.default_location_src_id.id,
            'product_min_qty': 1.0,
            'product_max_qty': 1.0,
        })

        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_stva.id,
                'pricelist_id': self.pos_config_usd.pricelist_id.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 10},
            ],
        })
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        purchase_order = self.env['purchase.order'].search([], limit=1)
        self.assertEqual(purchase_order.order_line.product_qty, 1)
        self.assertEqual(purchase_order.order_line.product_id.id,
                        self.ten_dollars_with_15_incl.product_variant_id.id)

    def test_pos_order_refund_ship_delay_totalcost(self):
        # test that the total cost is computed for refund with a shipping delay and an avco/fifo product
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        self.pos_config_usd.write({'ship_later': True})
        categ = self.env['product.category'].create({
            'name': 'test',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
        })
        product = self.env['product.product'].create({
            'name': 'Product A',
            'categ_id': categ.id,
            'lst_price': 10,
            'standard_price': 10,
            'is_storable': True,
        })
        productB = self.env['product.product'].create({
            'name': 'Product B',
            'categ_id': categ.id,
            'lst_price': 10,
            'standard_price': 10,
            'is_storable': True,
        })

        order_data = {
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'lines': [[0, 0, {
                'name': "OL/0001",
                'product_id': product.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 20,
                'price_subtotal_incl': 20,
                'total_cost': 20,
            }], [0, 0, {
                'name': "OL/0001",
                'product_id': productB.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 20,
                'price_subtotal_incl': 20,
                'total_cost': 20,
            }]],
            'payment_ids': [(0, 0, {
                'amount': 20,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id
            })],
            'amount_paid': 20.0,
            'amount_total': 20.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
            }
        self.env['pos.order'].sync_from_ui([order_data])
        order = current_session.order_ids[0]
        refund_values = [{
            'name': 'a new test refund order',
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'amount_paid': -10,
            'amount_tax': 0,
            'amount_return': 0,
            'amount_total': -10,
            'fiscal_position_id': False,
            'lines': [[0, 0, {
                'product_id': product.id,
                'price_unit': 10,
                'discount': 0,
                'qty': -2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': -20,
                'price_subtotal_incl': -20,
                'refunded_orderline_id': order.lines[0].id,
                'price_type': 'automatic'
            }], [0, 0, {
                'product_id': productB.id,
                'price_unit': 10,
                'discount': 0,
                'qty': -2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': -20,
                'price_subtotal_incl': -20,
                'refunded_orderline_id': order.lines[1].id,
                'price_type': 'automatic'
            }]],
            'shipping_date': fields.Date.today(),
            'sequence_number': 2,
            'to_invoice': True,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'uuid': '12345-123-1234',
            'payment_ids': [[0, 0, {
                'amount': -10,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id
            }]],
            'is_refund': True,
        }]
        self.env['pos.order'].sync_from_ui(refund_values)
        refunded_order_line = self.env['pos.order.line'].search([('product_id', '=', product.id), ('qty', '=', -2)])
        self.assertEqual(refunded_order_line.total_cost, -20)

    def test_sum_only_pos_locations(self):
        """Test that quantities are summed only from POS source locations"""

        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'tracking': 'lot',
            'is_storable': True,
        })

        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })

        self.pos_child_location = self.env['stock.location'].create({
            'name': 'POS Child Location',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })

        self.other_location = self.env['stock.location'].create({
            'name': 'Other Location',
            'usage': 'internal',
        })

        picking_type = self.env['stock.picking.type'].create({
            'name': 'POS Operations',
            'code': 'outgoing',
            'sequence_code': 'POS',
            'warehouse_id': self.warehouse.id,
            'default_location_src_id': self.warehouse.lot_stock_id.id,
        })

        self.pos_config = self.env['pos.config'].create({
            'name': 'Test POS Config',
            'picking_type_id': picking_type.id,
        })

        self.lot = self.env['stock.lot'].create({
            'name': 'TEST_LOT',
            'product_id': self.product.id,
        })

        # Create quants in different locations for the same lot
        self.env['stock.quant'].create([{
            'product_id': self.product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'lot_id': self.lot.id,
            'quantity': 10.0,
        }, {
            'product_id': self.product.id,
            'location_id': self.pos_child_location.id,
            'lot_id': self.lot.id,
            'quantity': 5.0,
        }, {
            'product_id': self.product.id,
            'location_id': self.other_location.id,
            'lot_id': self.lot.id,
            'quantity': 20.0,
        }])

        result = self.env['pos.order.line'].get_existing_lots(self.env.company.id, self.pos_config.id, self.product.id)

        self.assertEqual(len(result), 1, "Should return exactly one lot")
        self.assertEqual(result[0]['name'], 'TEST_LOT')
        self.assertEqual(result[0]['product_qty'], 15.0, "Should sum only quantities from POS source locations")

    def test_order_refund_lot_valuated(self):
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
            'lot_valuated': True,
            'lst_price': 500.0
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product2.id,
            'inventory_quantity': 10,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
            'lot_id': self.env['stock.lot'].create({'name': '1001', 'product_id': product2.id}).id,
        }).sudo().action_apply_inventory()

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        # I create a new PoS order with 2 lines
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.partner.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product2.id,
                'price_unit': 500,
                'discount': 0,
                'qty': 1.0,
                'tax_ids': [],
                'price_subtotal': 500,
                'price_subtotal_incl': 500,
                'pack_lot_ids': [Command.create({'lot_name': '1001'})]
            })],
            'amount_total': 500.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.assertAlmostEqual(order.amount_total, order.amount_paid, msg='Order should be fully paid.')

        # I create a refund
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()
        current_session.close_session_from_ui()
        self.assertEqual(current_session.picking_ids.mapped('state'), ['done', 'done'])

    def test_search_paid_order_ids(self):
        """ Test if the orders from other configs are excluded in search_paid_order_ids """
        other_pos_config = self.env['pos.config'].create({
            'name': 'Other POS',
            'picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1).id,
        })
        self.pos_config_usd.open_ui()
        other_pos_config.open_ui()
        current_session = self.pos_config_usd.current_session_id
        other_session = other_pos_config.current_session_id

        paid_order_1, paid_order_2 = self.env['pos.order'].create([{
            'company_id': self.env.company.id,
            'session_id': session_id,
            'partner_id': self.partner.id,
            'lines': [
                Command.create({
                    'product_id': self.product_a.id,
                    'qty': 1,
                    'price_subtotal': 134.38,
                    'price_subtotal_incl': 134.38,
                }),
            ],
            'amount_tax': 0.0,
            'amount_total': 134.38,
            'amount_paid': 134.38,
            'amount_return': 0.0,
            'state': 'paid',
        } for session_id in (current_session.id, other_session.id)])

        order_ids = [oi[0] for oi in self.env['pos.order'].search_paid_order_ids(other_pos_config.id, [], 80, 0)['ordersInfo']]
        self.assertNotIn(paid_order_1.id, order_ids)
        self.assertIn(paid_order_2.id, order_ids)

        order_ids = [oi[0] for oi in self.env['pos.order'].search_paid_order_ids(other_pos_config.id, [('partner_id.complete_name', 'ilike', self.partner.complete_name)], 80, 0)['ordersInfo']]
        self.assertNotIn(paid_order_1.id, order_ids)
        self.assertIn(paid_order_2.id, order_ids)

    def test_split_payment_linked_to_accounting_partner(self):
        self.bank_payment_method.write({'split_transactions': True})
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        child_partner = self.env['res.partner'].create({
            'name': 'partner1 child',
            'parent_id': self.partner.id
        })
        product_order = {
            'amount_paid': 750,
            'amount_tax': 0,
            'amount_return': 0,
            'amount_total': 750,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'lines': [[0, 0, {
                'discount': 0,
                'pack_lot_ids': [],
                'price_unit': 750.0,
                'product_id': self.product.id,
                'price_subtotal': 750.0,
                'price_subtotal_incl': 750.0,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            }]],
            'name': 'Order 12345-123-1234',
            'partner_id': child_partner.id,
            'session_id': current_session.id,
            'sequence_number': 2,
            'payment_ids': [[0, 0, {
                'amount': 750,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id
            }]],
            'uuid': '12345-123-1234',
            'user_id': self.env.uid,
            'to_invoice': False}

        self.env['pos.order'].sync_from_ui([product_order])
        current_session.close_session_from_ui()
        order_balance = current_session.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
            and l.partner_id == self.partner
        ).balance
        payment_balance = current_session.bank_payment_ids.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
            and l.partner_id == self.partner
        ).balance
        self.assertEqual(order_balance + payment_balance, 0)
