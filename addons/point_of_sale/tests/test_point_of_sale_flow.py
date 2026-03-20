import odoo

from unittest.mock import patch
from odoo import fields
from odoo.fields import Command
from datetime import datetime, timedelta
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.exceptions import ValidationError


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):

    def setup_tags(self):
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

        return tags

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
        self.assertTrue(refund.payment_ids.payment_method_id.type == 'cash')
        # refund lines should be positive
        self.assertEqual(refund.lines[0].price_subtotal_incl, 10.0)
        self.assertEqual(refund.lines[1].price_subtotal_incl, 20.0)

        current_session = self.pos_config_usd.current_session_id
        closing_data = current_session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        current_session.close_session_from_ui({
            self.cash_payment_method.id: expected_cashbox_amount,
        })
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

    def test_pos_orders_count(self):
        parent_partner = self.env['res.partner'].create({
            'name': 'Parent Partner',
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Child Partner',
            'parent_id': parent_partner.id
        })
        order_1, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': parent_partner.id,
            },
            'line_data': [
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 20},
            ],
        })
        order_2, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': child_partner.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 10},
            ],
        })
        self.assertEqual(len(order_1), 1, "Expected 1 order directly on parent partner")
        self.assertEqual(len(order_2), 1, "Expected 1 order directly on child partner")
        self.assertEqual(parent_partner.pos_order_count, 2, "Parent partner should see 2 orders including child’s")
        self.assertEqual(child_partner.pos_order_count, 1, "Child partner should see only their own order")

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

        # Making the invoice draft should send a warning notification to the user
        with patch.object(self.env.registry['bus.bus'], '_sendone') as mock_send:
            invoice.button_draft()
            mock_send.assert_called_with(self.env.user, 'simple_notification', {
                'type': 'danger',
                'message': "You can't reset this invoice to draft because the POS session is still open. Please close the ongoing session first, then try again.",
                'sticky': True,
            })

        self.assertEqual(invoice.state, 'posted')

        self.assertAlmostEqual(invoice.amount_total, order.amount_total, places=2)

        for iline in invoice.invoice_line_ids:
            self.assertFalse(iline.tax_ids)

        self.pos_config_usd.current_session_id.close_session_from_ui()

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
        })

        pos_order.action_pos_order_invoice()
        invoice = pos_order.account_move

        self.assertEqual(
            invoice.partner_shipping_id.id,
            delivery2.id,
            "The shipping address should be 'Delivery Address 2' as selected in the POS order."
        )

    def test_pos_order_invoice_payment_term(self):
        """ Test that when invoicing a POS order paid with customer account, the partner's payment term is then applied to the invoice. """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'type': 'pay_later',
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

        current_session.close_session_from_ui()
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        credit_notes = self.env['account.move'].search([('move_type', '=', 'out_refund')], order='id desc', limit=1)
        self.assertEqual(credit_notes.ref, "Reversal of: "+invoices.name)
        self.assertEqual(credit_notes.reversed_entry_id.id, invoices.id)

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
        current_session.close_session_from_ui()
        refund_payment = refund.payment_ids[0]
        self.assertEqual(refund_payment.amount, -25.0)
        self.assertEqual(refund.amount_total, -23.00)
        self.assertEqual(refund.amount_paid, -25.0)
        self.assertEqual(current_session.state, 'closed')

    def test_pos_branch_payment_method_config(self):
        """ This test checks that we don't set a config on a payment
        method that have different companies.
        """
        branch = self.env['res.company'].create({
            'name': 'Sub Company',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        self.env.cr.precommit.run()
        self.env.user.group_ids += self.env.ref('point_of_sale.group_pos_manager')
        bank_payment_method = self.bank_payment_method.copy()
        sub_pos_config = self.env['pos.config'].with_company(branch).create({
            'name': 'Main',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaises(ValidationError, msg="The points of sale for the payment method Bank must belong to its company."):
            bank_payment_method.write({"config_ids": sub_pos_config.ids})

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

        self.pos_config_usd.current_session_id.close_session_from_ui()
        order_lot_id = order.picking_ids.move_line_ids.lot_id
        self.assertEqual(order_lot_id.name, '1001')
        self.assertTrue(all(
            quant.lot_id == order_lot_id
            for quant in self.env['stock.quant'].search([
                ('product_id', '=', self.ten_dollars_with_10_incl.product_variant_id.id)
            ])
        ))

    def test_order_existing_lot_gs1_nomenclature(self):
        """An existing lot whose name is also a valid GS1 barcode (e.g. "10156":
        AI "10" -> Batch/Lot) must still be found when the order is validated,
        instead of being recreated and raising a duplicate lot error.
        """
        if not self.env['ir.module.module'].search_count([('name', '=', 'stock_barcode'), ('state', '=', 'installed')]):
            self.skipTest("stock_barcode is not installed")
        gs1_nomenclature = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.env.company.nomenclature_id = gs1_nomenclature
        self.pos_config_usd.picking_type_id.write({
            'use_create_lots': True,
            'use_existing_lots': True,
        })
        product = self.ten_dollars_with_10_incl.product_variant_id
        product.write({
            'tracking': 'lot',
            'is_storable': True,
        })

        order_data = {
            'line_data': [{
                'product_id': product.id,
                'pack_lot_ids': [Command.create({'lot_name': '10156'})],
            }],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
            ],
        }
        order1, _ = self.create_backend_pos_order(order_data)
        lot = order1.picking_ids.move_line_ids.lot_id
        self.assertEqual(lot.name, '10156')

        order2, _ = self.create_backend_pos_order(order_data)
        self.pos_config_usd.current_session_id.close_session_from_ui()

        self.assertEqual(order2.state, 'done')
        self.assertEqual(order2.picking_ids.move_line_ids.lot_id, lot)

    def test_pos_creation_in_branch(self):
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })

        self.env["pos.config"].with_company(branch).create({
            "name": "Branch Point of Sale"
        })

    def test_change_with_card_only(self):
        """Test that the change is not skipped if order was overpaid only with card"""
        self.pos_config_usd.open_ui()
        pos_session = self.pos_config_usd.current_session_id
        cash_payment_method = pos_session.payment_method_ids.filtered(
            lambda pm: pm.type == 'cash',
        )[:1]
        product_order = {
            'amount_paid': 500,
            'amount_return': -50,
            'amount_tax': 0,
            'amount_total': 450,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'lines': [Command.create({
                'discount': 0,
                'id': 42,
                'price_unit': 450.0,
                'product_id': self.product.id,
                'price_subtotal': 450.0,
                'price_subtotal_incl': 450.0,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            })],
            'name': 'Order 12346-123-1234',
            'partner_id': self.partner.id,
            'session_id': pos_session.id,
            'sequence_number': 2,
            'payment_ids': [Command.create({
                'amount': 500,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id
            })],
            'uuid': '12346-123-1234',
            'user_id': self.env.uid,
            'to_invoice': True
        }
        pos_order_id = self.env['pos.order'].sync_from_ui([product_order])['pos.order'][0]['id']
        pos_order = self.env['pos.order'].search([('id', '=', pos_order_id)])
        payments = pos_order.payment_ids
        self.assertRecordValues(payments.sorted(), [
            {'amount': -50.0, 'payment_method_id': cash_payment_method.id, 'is_change': True},
            {'amount': 500.0, 'payment_method_id': self.bank_payment_method.id, 'is_change': False},
        ])
        order_account_move = pos_order.account_move
        self.assertEqual(order_account_move.amount_total, pos_order.amount_total)

        payment_term = order_account_move.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        payment_amount = payment_term.mapped('amount_currency')
        self.assertEqual(len(payment_term), 2)
        self.assertEqual(payment_amount, [500.0, -50.0])

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
            'user_id': self.env.uid
        }

        self.env['pos.order'].sync_from_ui([pos_order_data])
        order = current_session.order_ids[0]
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])
        self.assertEqual(order.lines[0].refunded_qty, 1)
        refund.cancel_order_from_pos()
        self.assertEqual(order.lines[0].refunded_qty, 0)

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
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
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
            'preset_id': preset_takeaway.id,
            'preset_time': fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=-2)),
        })
        order.cancel_order_from_pos()
        self.assertEqual(order.state, 'cancel')

    def _create_and_invoice_order(self):
        current_session = self.pos_config_usd.current_session_id
        order = self.env["pos.order"].create({
            "company_id": self.env.company.id,
            "session_id": current_session.id,
            "partner_id": self.partner.id,
            "lines": [[0, 0, {
                "name": "OL/0001",
                "product_id": self.product_a.id,
                "price_unit": 10,
                "qty": 1,
                "price_subtotal": 10,
                "price_subtotal_incl": 10,
                "total_cost": 10,
            }]],
            "amount_paid": 10,
            "amount_total": 10,
            "amount_tax": 0,
            "amount_return": 0,
            "to_invoice": True,
        })
        ctx = {"active_ids": [order.id], "active_id": order.id}
        self.env["pos.make.payment"].with_context(ctx).create({
            "amount": 10,
            "payment_method_id": self.cash_payment_method.id,
        }).with_context(ctx).check()
        res = order.action_pos_order_invoice()
        return self.env["account.move"].browse(res["res_id"])

    def test_pos_order_partner_bank_id(self):
        self.pos_config_usd.open_ui()
        # Case 1: journal bank allows out payment
        allowed_bank = self.env["res.partner.bank"].create({
            "account_number": "FR7612345678901234567890123",
            "partner_id": self.company.partner_id.id,
            "bank_name": "Test Bank",
            "allow_out_payment": True,
        })
        self.cash_payment_method.journal_id.bank_account_id = allowed_bank
        invoice = self._create_and_invoice_order()
        self.assertEqual(
            invoice.partner_bank_id,
            allowed_bank,
            "Invoice should use journal bank account when allowed."
        )

        # Case 2: journal bank not allowed + no company fallback
        self.pos_config_usd.open_ui()
        blocked_bank = self.env["res.partner.bank"].create({
            "account_number": "FR7612345678901234567890124",
            "partner_id": self.company.partner_id.id,
            "bank_name": "Test Bank",
        })
        self.cash_payment_method.journal_id.bank_account_id = blocked_bank
        invoice = self._create_and_invoice_order()
        self.assertNotEqual(
            invoice.partner_bank_id.id,
            blocked_bank.id,
            "Invoice should not use journal bank account when not allowed."
        )

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
            'amount_paid': 150,  # Should correspond to the total paid in payment_ids
            'amount_tax': 0,
            'amount_return': 0,  # Is computed by sync_from_ui
            'amount_total': 149.99,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'lines': [[0, 0, {
                'discount': 0,
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

        closing_data = current_session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        current_session.close_session_from_ui({
            self.cash_payment_method.id: expected_cashbox_amount,
        })

        pos_order = self.env['pos.order'].search([])
        pos_order.action_pos_order_invoice()
        self.assertEqual(pos_order.state, 'done')

    def test_search_order_ids(self):
        """ Test if the orders from other configs are excluded in search_order_ids """
        other_pos_config = self.env['pos.config'].create({
            'name': 'Other POS',
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

        cancelled_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': other_session.id,
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
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'state': 'cancel',
        })

        # paid filter: excludes other config and cancelled orders
        order_ids = [oi[0] for oi in self.env['pos.order'].search_order_ids(other_pos_config.id, [], 80, 0, state_filter='paid')['ordersInfo']]
        self.assertNotIn(paid_order_1.id, order_ids)
        self.assertIn(paid_order_2.id, order_ids)
        self.assertNotIn(cancelled_order.id, order_ids)

        order_ids = [oi[0] for oi in self.env['pos.order'].search_order_ids(other_pos_config.id, [('partner_id.complete_name', 'ilike', self.partner.complete_name)], 80, 0, state_filter='paid')['ordersInfo']]
        self.assertNotIn(paid_order_1.id, order_ids)
        self.assertIn(paid_order_2.id, order_ids)
        self.assertNotIn(cancelled_order.id, order_ids)

        # cancelled filter: excludes other config and paid orders
        order_ids = [oi[0] for oi in self.env['pos.order'].search_order_ids(other_pos_config.id, [], 80, 0, state_filter='cancelled')['ordersInfo']]
        self.assertNotIn(paid_order_1.id, order_ids)
        self.assertNotIn(paid_order_2.id, order_ids)
        self.assertIn(cancelled_order.id, order_ids)

    def test_open_ui_missing_country(self):
        """ Test that a POS can not be opened if it has no country """
        self.pos_config_usd.company_id.account_fiscal_country_id = False
        with self.assertRaises(ValidationError, msg="The company must have a fiscal country set."):
            self.pos_config_usd.open_ui()

    def test_branch_company_access_cost_currency_id(self):
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        user = self.env['res.users'].create({
            'name': 'Branch user',
            'login': 'branch_user',
            'email': 'branch@yourcompany.com',
            'group_ids': [(6, 0, [self.ref('base.group_user'), self.ref('point_of_sale.group_pos_user')])],
            'company_ids': [(4, branch.id)],
            'company_id': branch.id,
        })
        product = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'company_id': self.env.company.id,
        })
        config = self.env['pos.config'].with_company(branch).create({
            'name': 'Main',
            'company_id': branch.id,
        })
        config.payment_method_ids.filtered(lambda pm: pm.type == 'cash').unlink()

        config.open_ui()
        current_session = config.current_session_id

        order = self.env['pos.order'].with_user(user).with_company(branch).create({
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'company_id': branch.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 6,
                'price_subtotal_incl': 6,
            })],
            'amount_paid': 6.0,
            'amount_total': 6.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        order_line = order.lines[0]
        self.env.invalidate_all()
        order_line.with_user(user).with_company(branch)._compute_total_cost()

    def test_delete_res_partner_linked_to_pos_order(self):
        """ Test that a partner linked to a pos order cannot be deleted. """
        partner = self.env['res.partner'].create({
            'name': 'Partner test',
        })
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': partner.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product.id,
                'price_unit': 450,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 450,
                'price_subtotal_incl': 450,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': 450.0,
            'amount_total': 450.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        with self.assertRaises(ValidationError, msg='You cannot delete a customer that has point of sales orders. You can archive it instead.'):
            partner.unlink()

    def test_draft_orders_products_loading(self):
        """ Test that products are correctly loaded when limited product loading is enabled and there are draft orders. """
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 1)
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        self.env['pos.order'].create([{
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner.id,
            'lines': [
                Command.create({
                    'product_id': product.id,
                    'qty': 1,
                    'price_subtotal': 1,
                    'price_subtotal_incl': 1,
                }),
            ],
            'amount_tax': 0.0,
            'amount_total': 1,
            'amount_paid': 1,
            'amount_return': 0.0,
            'state': 'draft',
        } for product in (self.product_a, self.product_b)])

        data = current_session.with_context(pos_limited_loading=True).load_data([])
        loaded_product_ids = [p['id'] for p in data['product.product']]
        self.assertIn(self.product_a.id, loaded_product_ids)
        self.assertIn(self.product_b.id, loaded_product_ids)

    def test_filter_local_data_no_errors(self):
        new_company = self.env['res.company'].create({
            'name': 'New Company',
            'country_id': self.env.company.country_id.id,
            'currency_id': self.env.company.currency_id.id,
        })
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        product = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': 200.0,
            'company_id': new_company.id,
        })
        self.env.transaction.clear()
        data = current_session.with_context(allowed_company_ids=self.env.company.ids).filter_local_data({'product.product': [product.id]})
        self.assertIn(product.id, data['product.product'])

    def test_string_sequence_number(self):
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        current_session.config_id.order_seq_id.prefix = '/AA'
        current_session.config_id.order_seq_id.suffix = '1.B'
        product_order = {
            'amount_paid': 750,
            'amount_tax': 0,
            'amount_return': 0,
            'amount_total': 750,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'lines': [[0, 0, {
                'price_unit': 750.0,
                'product_id': self.product.id,
                'price_subtotal': 750.0,
                'price_subtotal_incl': 750.0,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            }]],
            'name': 'Order 12345-123-1234',
            'partner_id': False,
            'session_id': current_session.id,
            'payment_ids': [[0, 0, {
                'amount': 750,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id
            }]],
            'uuid': '12345-123-1234',
            'user_id': self.env.uid,
            'to_invoice': False}

        self.env['pos.order'].sync_from_ui([product_order])
        order = self.env['pos.order'].search([])
        self.assertEqual(order.name, f"/AA - {order.pos_reference.split('-')[-1]} - 1.B")

    def test_payment_method_sequence(self):
        self.env['pos.payment.method'].search([]).write({'active': False})
        _, pm_ids = self.pos_config_usd._create_journal_and_payment_methods()
        # The 4th one is the online payment method, which is not created without demo data,
        methods = self.env['pos.payment.method'].browse(pm_ids)[:3]
        self.assertEqual(methods.mapped('name'), ['Cash', 'Card', 'Customer Account'])
        self.assertEqual(methods.mapped('sequence'), [1, 2, 4])
        new_pm = self.env['pos.payment.method'].create({'name': 'Quick Pay', 'type': 'bank'})
        self.assertEqual(new_pm.sequence, 5)

    def test_add_two_lines_with_same_uuid_through_sync_from_ui(self):
        """Test that adding two lines with the same UUID doesn't cause issues."""
        self.pos_config_usd.open_ui()
        order_data = {
            'line_data': [
                {'product_id': self.product.product_variant_id.id},
            ],
        }
        order, _ = self.create_backend_pos_order({**order_data})
        sync_from_ui_values = {
            "access_token": order.access_token,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "session_id": self.pos_config_usd.current_session_id.id,
            "company_id": self.env.company.id,
            "amount_tax": 0.0,
            "amount_total": 10.0,
            "amount_paid": 0,
            "amount_return": 0,
            "uuid": order.uuid,
            "id": order.id,
            "state": "draft",
            "lines": [
                [
                0,
                0,
                {
                    "product_id": self.product.product_variant_id.id,
                    "price_unit": 10.0,
                    "qty": 2,
                    "price_subtotal": 20.0,
                    "price_subtotal_incl": 20.0,
                    "tax_ids": [],
                    "uuid": order.lines[0].uuid,
                }
                ]
            ]
        }
        self.env['pos.order'].sync_from_ui([{
            **sync_from_ui_values,
        }])
        self.assertEqual(len(order.lines), 1, "Two lines with the same UUID were created")
        self.assertEqual(order.lines[0].qty, 2, "The quantity of the line should have been updated to 2")

    def test_manual_refund_negative_qty_invoice_creates_credit_note(self):
        """Invoicing a POS order created with negative qty (manual refund, no Refund action)
        must create a credit note (RINV/out_refund), not a customer invoice (INV)."""
        self.pos_config_usd.open_ui()

        # Create an order with negative qty only (no Refund action → is_refund stays False)
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_mobt.id,
                'pricelist_id': self.pos_config_usd.pricelist_id.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_no_tax.product_variant_id.id, 'qty': -1},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': -10},
            ],
        })

        self.assertEqual(order.state, 'paid')
        self.assertLess(order.amount_total, 0, 'Order total should be negative (manual refund).')
        self.assertFalse(order.is_refund, 'Order was not created via Refund action.')

        order.action_pos_order_invoice()

        self.assertTrue(order.account_move, 'An invoice/credit note should be created.')
        self.assertEqual(
            order.account_move.move_type,
            'out_refund',
            'Invoicing a manual refund (negative qty) must create a credit note (RINV), not a customer invoice.',
        )

    def test_pos_payment_direction_and_accounts(self):
        """Ensure POS payments create correct inbound/outbound payments and accounts and related journal items"""

        def _do_pos_transaction(amount, split, index):
            self.pos_config_usd.open_ui()
            current_session = self.pos_config_usd.current_session_id
            product_order = {
                'amount_paid': amount,
                'amount_tax': 0,
                'amount_return': 0,
                'amount_total': amount,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'lines': [[0, 0, {
                    'price_unit': 100.0,
                    'product_id': self.product.id,
                    'price_subtotal': amount,
                    'price_subtotal_incl': amount,
                    'qty': 1 if amount > 0 else -1,
                }]],
                'name': f'Order {index}',
                'partner_id': self.partner.id,
                'session_id': current_session.id,
                'payment_ids': [[0, 0, {
                    'amount': amount,
                    'payment_method_id': self.bank_payment_method.id
                }]],
                'uuid': f'12345-123-1253{index}',
                'user_id': self.env.uid,
                'to_invoice': False
            }
            self.env['pos.order'].sync_from_ui([product_order])
            current_session.close_session_from_ui()
            return current_session

        self.bank_payment_method.outstanding_account_id = self.inbound_payment_method_line.payment_account_id.id
        session_ids = [
            _do_pos_transaction(amount, split, idx).id
            for idx, (amount, split) in enumerate([(100, False), (-100, False), (100, True), (-100, True)])
        ]
        payments = self.env['account.payment'].search([('pos_session_id', 'in', session_ids)], order='id')
        receivable_account_id = self.env['pos.session'].browse(session_ids)._get_receivable_account()
        self.assertRecordValues(
            payments,
            [
                {
                    "payment_type": "inbound",
                    "outstanding_account_id": self.bank_payment_method.outstanding_account_id.id,
                    "destination_account_id": receivable_account_id.id,
                },
                {
                    "payment_type": "outbound",
                    "outstanding_account_id": self.bank_payment_method.outstanding_account_id.id,
                    "destination_account_id": receivable_account_id.id,
                },
                {
                    "payment_type": "inbound",
                    "outstanding_account_id": self.bank_payment_method.outstanding_account_id.id,
                    "destination_account_id": receivable_account_id.id,
                },
                {
                    "payment_type": "outbound",
                    "outstanding_account_id": self.bank_payment_method.outstanding_account_id.id,
                    "destination_account_id": receivable_account_id.id,
                },
            ],
        )

        for payment in payments:
            move_lines = payment.move_id.line_ids.sorted('balance')
            if payment.payment_type == "inbound":
                self.assertRecordValues(move_lines, [
                    {'account_id': receivable_account_id.id},
                    {'account_id': self.bank_payment_method.outstanding_account_id.id},
                ])
            else:
                self.assertRecordValues(move_lines, [
                    {'account_id': self.bank_payment_method.outstanding_account_id.id},
                    {'account_id': receivable_account_id.id},
                ])

    def test_pricelist_item_date_loading(self):
        """Pricelist items respect date_start/date_end on full and incremental loads."""
        pricelist = self.env['product.pricelist'].create({'name': 'Date Test Pricelist'})
        self.pos_config_usd.write({
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, pricelist.ids)],
            'pricelist_id': pricelist.id,
        })
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        now = fields.Datetime.now()
        item_data = {'pricelist_id': pricelist.id, 'compute_price': 'fixed', 'fixed_price': 10}

        item_no_dates = self.env['product.pricelist.item'].create(item_data)
        item_past_start = self.env['product.pricelist.item'].create({
            **item_data, 'date_start': now - timedelta(days=5),
        })
        item_future_start = self.env['product.pricelist.item'].create({
            **item_data, 'date_start': now + timedelta(days=5),
        })
        item_expired = self.env['product.pricelist.item'].create({
            **item_data, 'date_end': now - timedelta(days=1),
        })
        # date_start just became valid; will be fetched via the date_start window check.
        item_just_activated = self.env['product.pricelist.item'].create({
            **item_data, 'date_start': now - timedelta(days=3),
        })
        # Will be modified after last_server_date to bump its write_date.
        item_to_modify = self.env['product.pricelist.item'].create(item_data)

        # Backdate write_date for items that must appear stale during incremental load.
        old_date = now - timedelta(days=30)
        stale_items = item_future_start | item_just_activated | item_to_modify
        stale_items.flush_model()
        self.env.cr.execute(
            "UPDATE product_pricelist_item SET write_date = %s WHERE id IN %s",
            (old_date, tuple(stale_items.ids)),
        )
        stale_items.invalidate_recordset(['write_date'])

        # --- Full load ---
        data = session.load_data([])
        loaded_ids = {i['id'] for i in data['product.pricelist.item']}
        self.assertIn(item_no_dates.id, loaded_ids)
        self.assertIn(item_past_start.id, loaded_ids)
        self.assertIn(item_just_activated.id, loaded_ids)
        self.assertNotIn(item_future_start.id, loaded_ids)
        self.assertNotIn(item_expired.id, loaded_ids)

        # --- Incremental load ---
        # last_server_date = 10 days ago; item_just_activated has write_date = 30 days ago
        # so write_date < last_server_date, but date_start (3 days ago) > last_server_date
        last_server_date = fields.Datetime.to_string(now - timedelta(days=10))

        # Modify item_to_modify now (write_date = now > last_server_date).
        item_to_modify.write({'fixed_price': 99})

        data = session.with_context(pos_last_server_date=last_server_date).load_data([])
        loaded_ids = {i['id'] for i in data['product.pricelist.item']}
        self.assertIn(item_just_activated.id, loaded_ids,
            "item whose date_start fell inside the sync window must be fetched on incremental load")
        self.assertIn(item_to_modify.id, loaded_ids,
            "item modified after last_server_date must be fetched on incremental load")
        self.assertNotIn(item_future_start.id, loaded_ids,
            "item with date_start still in the future must not be fetched")

    def test_sequence_dynamic_prefix_suffix(self):
        """Test that sequence_number is correctly extracted when sequence has dynamic prefix/suffix."""
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        # Use dynamic prefix and suffix with static hyphen separators
        current_session.config_id.order_seq_id.prefix = 'POS-%(year)s'
        current_session.config_id.order_seq_id.suffix = '-%(month)s'

        product_order = {
            'amount_paid': 750,
            'amount_tax': 0,
            'amount_return': 0,
            'amount_total': 750,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'lines': [[0, 0, {
                'price_unit': 750.0,
                'product_id': self.product.id,
                'price_subtotal': 750.0,
                'price_subtotal_incl': 750.0,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            }]],
            'name': 'Order 12345-123-1234',
            'partner_id': False,
            'session_id': current_session.id,
            'payment_ids': [[0, 0, {
                'amount': 750,
                'name': fields.Datetime.now(),
                'payment_method_id': self.bank_payment_method.id
            }]],
            'uuid': '12345-123-1234',
            'user_id': self.env.uid,
            'to_invoice': False
        }

        self.env['pos.order'].sync_from_ui([product_order])
        order = self.env['pos.order'].search([])

        # Verify order name contains interpolated year and month with static parts
        current_year = fields.Datetime.now().year
        current_month = fields.Datetime.now().strftime('%m')

        self.assertIn(f'POS-{current_year}', order.name,
            f"Order name should contain 'POS-{current_year}', got: {order.name}")
        self.assertIn(f'-{current_month}', order.name,
            f"Order name should contain '-{current_month}', got: {order.name}")
