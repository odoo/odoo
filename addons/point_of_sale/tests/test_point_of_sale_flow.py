import odoo

from freezegun import freeze_time
from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from datetime import datetime, timedelta
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_order_refund(self):
        self.pos_config_usd.open_ui()

        # The amount_total will be 30 with 3.52 taxes included
        order, refund = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
                {'payment_method_id': self.bank_payment_method.id, 'amount': 20},
            ],
            'refund_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': -30},
            ]
        })

        self.assertAlmostEqual(order.amount_total, order.amount_paid)
        self.assertEqual(refund.state, 'paid', "The refund is not marked as paid")
        self.assertTrue(refund.payment_ids.payment_method_id.is_cash_count)

        current_session = self.pos_config_usd.current_session_id
        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(
            lambda payment: payment.payment_method_id.type == 'cash').mapped('amount')
        )
        current_session.post_closing_cash_details(total_cash_payment)
        current_session.close_session_from_ui()
        self.assertEqual(current_session.state, 'closed')

    def test_refund_multiple_payment_rounding(self):
        """
            This test makes sure that the refund amount always correspond to what
            has been paid in the original order. In this example we have a
            rounding, so we pay 5 in bank that is not rounded, then we pay the
            rest in cash that is rounded. This sum up to 10 paid, so the refund
            should be 10.
        """
        self.account_cash_rounding_down.rounding = 5.0
        self.pos_config_usd.write({
            'rounding_method': self.account_cash_rounding_down.id,
            'cash_rounding': True,
        })

        self.pos_config_usd.open_ui()
        # order total will be 11.5 with 1.5 taxes excluded, with rounding 10 should be paid
        order, refund = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_15_excl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 5},
                {'payment_method_id': self.cash_payment_method.id},
            ],
            'refund_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': -10},
            ]
        })

        self.assertEqual(order.amount_paid, 10.0)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(refund.amount_paid, -10.0)
        self.assertEqual(refund.state, 'paid')

    def test_order_partial_refund_rounding(self):
        """ This test ensures that the refund amound of a partial order corresponds to
        the price of the item, without rounding. """
        self.account_cash_rounding_down.rounding = 5.0
        self.pos_config_usd.write({
            'rounding_method': self.account_cash_rounding_down.id,
            'cash_rounding': True,
        })

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        # order total will be 34.5 with 4.5 taxes excluded, with rounding 10 should be paid
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_15_excl.product_variant_id.id, 'qty': 3},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 34.5},
            ],
        })

        self.assertEqual(order._get_rounded_amount(order.amount_total), order.amount_paid)
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = 1
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, 10.0)
        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()
        self.assertEqual(refund.state, 'paid')
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed')

    def test_order_partial_refund(self):
        """ The purpose of this test is to make a partial refund of a pos order.
        The amount to refund should depend on the article returned and once the
        payment made, the refund order should be marked as paid."""
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        # order total will be 30 with 3.52 taxes included
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
                {'payment_method_id': self.bank_payment_method.id, 'amount': 20},
            ]
        })

        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = 0
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, -20.0)

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        self.assertEqual(refund.state, 'paid')
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed')

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
        invoice_pdf_content = str(order_refund_3.account_move._get_invoice_legal_documents(
            'pdf', allow_fallback=True).get('content'))
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

    def test_order_to_payment_currency(self):
        """
            In order to test the Point of Sale in module, I will do a full flow
            from the sale to the payment and invoicing. I will use two products,
            one with price including a 10% tax, the other one with 5% tax
            excluded from the price.

            The order will be in a different currency than the company currency.
        """
        self.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [self.env.ref('base.USD').id, self.env.company.id])

        # Demo data are crappy, clean-up the rates
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': self.env.ref('base.EUR').id,
        })

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_mobt.id,
                'pricelist_id': self.partner_mobt.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_no_tax.product_variant_id.id},
                {'product_id': self.twenty_dollars_no_tax.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 10},
                {'payment_method_id': self.bank_payment_method.id},
            ],
            'pos_config': self.pos_config_eur,
        })

        self.assertEqual(order.amount_total, 30)
        self.assertEqual(order.amount_paid, 30)
        self.assertEqual(order.state, 'paid')
        current_session = self.pos_config_eur.current_session_id
        current_session.action_pos_session_validate()
        self.assertTrue(current_session.move_id)
        debit_lines = current_session.move_id.mapped('line_ids.debit')
        credit_lines = current_session.move_id.mapped('line_ids.credit')
        amount_currency_lines = current_session.move_id.mapped('line_ids.amount_currency')
        for a, b in zip(sorted(debit_lines), [0.0, 15.0]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(credit_lines), [0.0, 15.0]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(amount_currency_lines), [-30, 30]):
            self.assertAlmostEqual(a, b)

    def test_order_to_invoice_no_tax(self):
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_mobt.id,
                'pricelist_id': self.partner_mobt.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_no_tax.product_variant_id.id},
                {'product_id': self.twenty_dollars_no_tax.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 30},
            ],
        })
        self.assertEqual(order.state, 'paid', "Order should be in paid state.")
        self.assertFalse(order.account_move, 'Invoice should not be attached to order yet.')

        res = order.action_pos_order_invoice()
        self.assertIn('res_id', res, "No invoice created")

        # I test that the total of the attached invoice is correct
        invoice = self.env['account.move'].browse(res['res_id'])
        if invoice.state != 'posted':
            invoice.action_post()
        self.assertAlmostEqual(invoice.amount_total, order.amount_total, places=2)

        for iline in invoice.invoice_line_ids:
            self.assertFalse(iline.tax_ids)

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

    def test_order_with_deleted_tax(self):
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_excl.product_variant_id.id},
            ],
        })

        untax, atax = self.compute_tax(self.ten_dollars_with_10_excl.product_variant_id, 10.0)
        self.ten_dollars_with_10_excl.taxes_id.unlink()
        current_session = self.pos_config_usd.current_session_id
        payment = self.env['pos.make.payment'].create({
            'config_id': self.pos_config_usd.id,
            'amount': untax + atax,
            'payment_method_id': self.cash_payment_method.id,
        })
        payment.with_context(active_ids=order.ids, active_id=order.id).check()
        self.assertEqual(order.state, 'paid', "Order should be in paid state.")

        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(
            lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        current_session.post_closing_cash_details(total_cash_payment)

        # close session (should not fail here)
        # We don't call `action_pos_session_closing_control` to force the failed
        # closing which will return the action because the internal rollback call messes
        # with the rollback of the test runner. So instead, we directly call the method
        # that returns the action by specifying the imbalance amount.
        action = current_session._close_session_action(1.0)
        wizard = self.env['pos.close.session.wizard'].browse(action['res_id'])
        wizard.with_context(action['context']).close_session()

        diff_line = current_session.move_id.line_ids.filtered(
            lambda line: line.name == 'Difference at closing PoS session')
        self.assertAlmostEqual(diff_line.credit, 1.0, msg="Missing amount of 1.0")

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

    def test_pos_order_invoice_payment_term(self):
        """ Test that when invoicing a POS order paid with customer account, the partner's payment term is then applied to the invoice. """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        payment_methods = self.pos_config_usd.payment_method_ids | self.customer_account_payment_method
        self.pos_config_usd.write({'payment_method_ids': [Command.set(payment_methods.ids)]})

        pay_term_30 = self.env.ref('account.account_payment_term_30days')
        partner_a = self.env["res.partner"].create({
            'name': 'APartner',
            'property_payment_term_id': pay_term_30.id,
        })

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': partner_a.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
        })
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 10.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        self.assertEqual(order.account_move.invoice_date_due, (datetime.now() + timedelta(days=30)).date())

    def test_order_with_different_payments_and_refund(self):
        """
        Test that all the payments are correctly taken into account when the order
        contains multiple payments and money refund.
        In this example, we create an order with two payments for a product of 750$:
            - one payment of $300 with customer account
            - one payment of $460 with cash
        Then, we refund the order with $10, and check that the amount still due is 300$.
        """
        self.twenty_dollars_no_tax.product_variant_id.write({
            'is_storable': True,
        })
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_adgu.id,
                'to_invoice': True,
            },
            'line_data': [
                {'product_id': self.twenty_dollars_no_tax.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
                {'payment_method_id': self.credit_payment_method.id, 'amount': 20},
                {'payment_method_id': self.cash_payment_method.id, 'amount': -10},
            ],
        })
        self.assertEqual(order.account_move.amount_residual, 20)

    def test_sale_order_postponed_invoicing(self):
        """
            Test the flow of creating an invoice later, after the POS session
            has been closed and everything has been processed. Process should:
                - Create a new misc entry, that will revert part of the POS
                    closing entry.
                - Create the move and associating payment(s) entry, as it would
                    do when closing with invoice.
                - Reconcile the receivable lines from the created misc entry
                    with the ones from the created payment(s)
        """
        tags = self.env['account.account.tag'].create([
            {
                'name': f"tag{i}",
                'applicability': 'taxes',
                'country_id': self.company_data['company'].country_id.id,
            }
            for i in range(1, 5)
        ])

        self.twenty_dollars_with_15_excl.taxes_id = [Command.set(self.tax_sale_a.ids)]
        self.tax_sale_a.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'base').write({'tag_ids': tags[0].ids})
        self.tax_sale_a.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'tax').write({'tag_ids': tags[1].ids})
        self.tax_sale_a.refund_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'base').write({'tag_ids': tags[2].ids})
        self.tax_sale_a.refund_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'tax').write({'tag_ids': tags[3].ids})

        with freeze_time('2020-01-01'):
            order, _ = self.create_backend_pos_order({
                'line_data': [
                    {'product_id': self.twenty_dollars_with_15_excl.product_variant_id.id},
                ],
                'payment_data': [
                    {'payment_method_id': self.bank_payment_method.id, 'amount': 23.0},
                ],
            })
            self.pos_config_usd.current_session_id.action_pos_session_closing_control()

            # Check the closing entry.
            closing_entry = order.session_move_id
            self.assertRecordValues(closing_entry.line_ids.sorted(), [{
                    'balance': -3.0,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'tax_ids': [],
                    'tax_tag_ids': tags[1].ids,
                    'tax_tag_invert': True,
                    'reconciled': False
                }, {
                    'balance': -20.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': self.tax_sale_a.ids,
                    'tax_tag_ids': tags[0].ids,
                    'tax_tag_invert': True,
                    'reconciled': False
                }, {
                    'balance': 23.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                    'tax_ids': [],
                    'tax_tag_ids': [],
                    'tax_tag_invert': False,
                    'reconciled': True
            }])

        with freeze_time('2020-01-03'):
            order.partner_id = self.partner_adgu.id
            order.action_pos_order_invoice()

        # Check the reverse moves, one for the closing entry, one for the statement lines.
        reverse_closing_entries = self.env['account.move'].search([
            ('id', '!=', closing_entry.id),
            ('company_id', '=', self.env.company.id),
            ('statement_line_id', '=', False),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
        ])
        self.assertRecordValues(reverse_closing_entries[0].line_ids.sorted(), [{
                'balance': 3.0,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'tax_ids': [],
                'tax_tag_ids': tags[1].ids,
                'tax_tag_invert': True,
                'reconciled': False
            }, {
                'balance': 20.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': self.tax_sale_a.ids,
                'tax_tag_ids': tags[0].ids,
                'tax_tag_invert': True,
                'reconciled': False
            }, {
                'balance': -23.0,
                'account_id': self.company_data['default_account_receivable'].id,
                'tax_ids': [],
                'tax_tag_ids': [],
                'tax_tag_invert': False,
                'reconciled': True
        }])
        self.assertRecordValues(reverse_closing_entries[2].line_ids.sorted(), [{
                'balance': -23.0,
                'account_id': self.company_data['default_account_receivable'].id,
                'tax_ids': [],
                'tax_tag_ids': [],
                'tax_tag_invert': False,
                'reconciled': True
            }, {
                'balance': 23.0,
                'account_id': self.company_data['default_account_receivable'].id,
                'tax_ids': [],
                'tax_tag_ids': [],
                'tax_tag_invert': False,
                'reconciled': True
        }])

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

    def test_order_pos_tax_same_as_company(self):
        """
            Test that when the default_pos_receivable_account and the partner
            account_receivable are the same, payment are correctly reconciled
            and the invoice is correctly marked as paid.
        """
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        account = self.partner_jcb.property_account_receivable_id
        current_session.company_id.account_default_pos_receivable_account_id = account

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_jcb.id,
                'to_invoice': True,
                'pricelist_id': self.partner_jcb.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 30},
            ],
        })

        self.assertEqual(order.account_move.amount_residual, 0)

    def test_journal_entries_category_without_account(self):
        # Set company's default accounts to false
        self.env.company.income_account_id = False
        self.env.company.expense_account_id = False
        self.twenty_dollars_with_10_incl.write({
            'property_account_income_id': False,
            'property_account_expense_id': False,
        })
        account = self.env['account.account'].create({
            'name': 'Account for category without account',
            'code': 'X1111',
        })

        self.pos_config_usd.journal_id.default_account_id = account.id
        self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 20},
            ],
        })
        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.move_id.line_ids[0].account_id.id, account.id)

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

    def test_order_refund_with_invoice(self):
        """This test make sure that credit notes of pos orders are correctly
           linked to the original invoice."""
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_adgu.id,
                'to_invoice': True,
            },
            'line_data': [
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id}
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 20}
            ],
            'refund_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': -20}
            ]
        })

        current_session.action_pos_session_closing_control()
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        credit_notes = self.env['account.move'].search([('move_type', '=', 'out_refund')], order='id desc', limit=1)
        self.assertEqual(credit_notes.ref, "Reversal of: "+invoices.name)
        self.assertEqual(credit_notes.reversed_entry_id.id, invoices.id)

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

    def test_no_default_pricelist(self):
        """Should not have default_pricelist if use_pricelist is false."""

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        self.pos_config_usd.write({
            'pricelist_id': pricelist.id,
            'use_pricelist': False,
        })
        self.pos_config_usd.open_ui()
        loaded_data = self.pos_config_usd.current_session_id.load_data([])

        self.assertFalse(loaded_data['pos.config'][0]['pricelist_id'], False)

    def test_refund_rounding_backend(self):
        self.account_cash_rounding_up.rounding = 5.0
        self.pos_config_usd.write({
            'rounding_method': self.account_cash_rounding_up.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        _, refund = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.twenty_dollars_with_15_excl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 23.0}
            ],
            'refund_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control()
        refund_payment = refund.payment_ids[0]
        self.assertEqual(refund_payment.amount, -25.0)
        self.assertEqual(refund.amount_total, -23.00)
        self.assertEqual(refund.amount_paid, -25.0)
        self.assertEqual(current_session.state, 'closed')

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

    def test_pos_branch_account(self):
        branch = self.env['res.company'].create({
            'name': 'Sub Company',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        self.env.cr.precommit.run()
        self.env.user.group_ids += self.env.ref('point_of_sale.group_pos_manager')
        bank_payment_method = self.bank_payment_method.copy()
        bank_payment_method.company_id = branch.id
        sub_pos_config = self.env['pos.config'].with_company(branch).create({
            'name': 'Main',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_journal_id': self.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, bank_payment_method.id)],
        })

        sub_pos_config.open_ui()
        current_session = sub_pos_config.current_session_id
        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_moda.id,
                'pricelist_id': sub_pos_config.pricelist_id.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': bank_payment_method.id},
            ],
            'pos_config': sub_pos_config,
        })

        current_session = sub_pos_config.current_session_id
        sub_pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed', msg='State of current session should be closed.')

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
        order_lot_id = order.picking_ids.move_line_ids_without_package.lot_id
        self.assertEqual(order_lot_id.name, '1001')
        self.assertTrue(all(
            quant.lot_id == order_lot_id
            for quant in self.env['stock.quant'].search([
                ('product_id', '=', self.ten_dollars_with_10_incl.product_variant_id.id)
            ])
        ))

    def test_pos_creation_in_branch(self):
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })

        self.env["pos.config"].with_company(branch).create({
            "name": "Branch Point of Sale"
        })

    def test_reordering_rules_triggered_closing_pos(self):
        if self.env['ir.module.module']._get('purchase').state != 'installed':
            self.skipTest("Purchase module is required for this test to run")

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

    def test_state_when_closing_register(self):
        self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 10},
            ],
        })
        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_payment_method.id: 5.00})
        self.assertEqual(current_session.state, 'closed')

    def test_refund_qty_refund_cancel(self):
        """
        Test the refunded qty of an order, when the refund order has been cancelled
        """

        product1 = self.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 100,
            'type': 'consu',
        })

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        pos_order_data = {
            'amount_paid': 100,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 100,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'lines': [(0, 0, {
                'discount': 0,
                'pack_lot_ids': [],
                'price_unit': 100.0,
                'product_id': product1.id,
                'price_subtotal': 100.0,
                'price_subtotal_incl': 100.0,
                'qty': 1,
                'tax_ids': []
            })],
            'name': 'Order 12345-123-1234',
            'partner_id': False,
            'session_id': current_session.id,
            'sequence_number': 2,
            'payment_ids': [(0, 0, {
                'amount': 100,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id
            })],
            'uuid': '12345-123-1234',
            'last_order_preparation_change': '{}',
            'user_id': self.env.uid
        }

        self.env['pos.order'].sync_from_ui([pos_order_data])
        order = current_session.order_ids[0]
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])
        self.assertEqual(order.lines[0].refunded_qty, 1)
        refund.action_pos_order_cancel()
        self.assertEqual(order.lines[0].refunded_qty, 0)

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
        }]
        self.env['pos.order'].sync_from_ui(refund_values)
        refunded_order_line = self.env['pos.order.line'].search([('product_id', '=', product.id), ('qty', '=', -2)])
        self.assertEqual(refunded_order_line.total_cost, -20)

    def test_cancel_order_with_past_preset(self):
        # Test that cancelling an order with a past preset does not raise an error and does cancel the order.
        preset_takeaway = self.env['pos.preset'].create({
            'name': 'Takeaway',
        })
        self.pos_config_usd.write({
            'use_presets': True,
            'default_preset_id': preset_takeaway.id,
            'available_preset_ids': [(6, 0, [preset_takeaway.id])],
        })
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'name': 'Takeaway',
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
                'day_period': 'morning',
            }) for day in range(7)],
        })
        preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar
        })
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': False,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.env['product.product'].search([('available_in_pos', '=', True)], limit=1).id,
                'price_unit': 49.99,
                'discount': 0,
                'qty': 1,
                'tax_ids': [],
                'price_subtotal': 49.99,
                'price_subtotal_incl': 49.99,
            })],
            'pricelist_id': False,
            'amount_paid': 49.99,
            'amount_total': 49.99,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
            'last_order_preparation_change': '{}',
            'preset_id': preset_takeaway.id,
            'preset_time': fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=-2)),
        })
        order.action_pos_order_cancel()
        self.assertEqual(order.state, 'cancel')

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

    def test_payment_difference_accounting_items(self):
        """Verify that the amount of the accounting items are correct when closing a session with a payment difference."""
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 100,
        })
        # Make a sale paid by bank
        self.pos_config_usd.open_ui()
        session_id = self.pos_config_usd.current_session_id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session_id.id,
            'partner_id': False,
            'lines': [Command.create({
                'name': 'OL/0001',
                'product_id': self.product1.id,
                'price_unit': 100.00,
                'discount': 0,
                'qty': 1,
                'tax_ids': False,
                'price_subtotal': 100.00,
                'price_subtotal_incl': 100.00,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': 100.00,
            'amount_total': 100.00,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        # Make payment
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.bank_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        session_id.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_payment_method.id: -10.00})
        self.bank_payment_move = session_id._get_related_account_moves().filtered(lambda move: 'Combine Bank' in move.ref)
        self.assertRecordValues(self.bank_payment_move.line_ids.sorted('balance'), [{
            'balance': -100.0,
            'account_id': self.bank_payment_method.receivable_account_id.id,
        },
        {
            'balance': 10.0,
            'account_id': self.bank_payment_method.journal_id.loss_account_id.id,
        },
        {
            'balance': 90.0,
            'account_id': self.bank_payment_move.payment_ids.outstanding_account_id.id,
        }])

    def test_pos_order_partner_bank_id(self):
        # Setup a running session, with a paid pos order that is not invoiced
        self.pos_config_usd.open_ui()
        self.cash_payment_method.journal_id.bank_account_id = self.env['res.partner.bank'].create({
            'acc_number': 'FR7612345678901234567890123',
            'partner_id': self.company.partner_id.id,
            'bank_name': 'Test Bank',
        })
        current_session = self.pos_config_usd.current_session_id
        self.order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'lines': [[0, 0, {
                'name': "OL/0001",
                'product_id': self.product_a.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'tax_ids': [],
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
                'total_cost': 10,
            }]],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
            })
        context_make_payment = {"active_ids": [self.order.id], "active_id": self.order.id}
        self.pos_make_payment_0 = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'amount': 10.0,
            'payment_method_id': self.cash_payment_method.id,
        })
        context_payment = {'active_id': self.order.id}
        self.pos_make_payment_0.with_context(context_payment).check()
        res = self.order.action_pos_order_invoice()
        invoice = self.env['account.move'].browse(res['res_id'])
        self.assertEqual(invoice.partner_bank_id, self.cash_payment_method.journal_id.bank_account_id, "The invoice should have the partner's bank account set.")

    def test_invoice_rounding_overpaid_backend(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 0.05,
            'rounding_method': 'UP',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })

        self.product_a.write({
            'name': 'Product Test',
            'list_price': 149.99,
            'taxes_id': False,
        })

        self.pos_config_usd.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        pos_order_data = {
            'amount_paid': 149.99,
            'amount_tax': 0,
            'amount_return': 0.01,
            'amount_total': 149.99,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'lines': [[0, 0, {
                'discount': 0,
                'pack_lot_ids': [],
                'price_unit': 149.99,
                'product_id': self.product_a.id,
                'price_subtotal': 149.99,
                'price_subtotal_incl': 149.99,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            }]],
            'name': 'Order 12345-123-1234',
            'partner_id': self.partner.id,
            'session_id': current_session.id,
            'sequence_number': 2,
            'payment_ids': [[0, 0, {
                'amount': 100,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id
            }], [0, 0, {
                'amount': 50,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id
            }]],
            'uuid': '12345-123-1234',
            'user_id': self.env.uid,
            'to_invoice': False,
        }
        self.env['pos.order'].sync_from_ui([pos_order_data])

        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        current_session.post_closing_cash_details(total_cash_payment)
        current_session.close_session_from_ui()

        pos_order = self.env['pos.order'].search([])
        pos_order.action_pos_order_invoice()
        self.assertEqual(pos_order.state, 'done')
