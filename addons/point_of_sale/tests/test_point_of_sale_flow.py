# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from unittest.mock import patch

import odoo
from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from odoo.exceptions import ValidationError
from odoo.addons.point_of_sale.tests.common import CommonPosTest

# TODO-PARP:
# - Merge tests into the final feature-oriented files.
# - Remove duplicated session/order/payment helpers.


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):

    _test_user_groups = None  # FIXME list needed groups

    def test_order_refund(self):
        self.pos_config_usd.open_ui()

        # The amount_total will be 30 with 2.73 taxes included
        order = self.create_pos_order(
            [
                [self.ten_dollars_with_10_incl.product_variant_id],
                [self.twenty_dollars_with_10_incl.product_variant_id],
            ],
            payments=[[self.cash_pm, 10], [self.bank_pm, 20]],
        )
        refund = self.refund_pos_order(order, self.cash_pm, -30)

        self.assertAlmostEqual(order.amount_total, order.amount_paid)
        self.assertEqual(refund.state, 'paid', "The refund is not marked as paid")
        self.assertTrue(refund.payment_ids.payment_method_id.type == 'cash')
        # refund lines should be positive
        self.assertEqual(refund.lines[0].price_subtotal_incl, 10.0)
        self.assertEqual(refund.lines[1].price_subtotal_incl, 20.0)

        self.close_pos_session()

    def test_refund_multiple_payment_rounding(self):
        """
            This test makes sure that the refund amount always correspond to what
            has been paid in the original order. In this example we have a
            rounding, so we pay 5 in bank that is not rounded, then we pay the
            rest in cash that is rounded. This sum up to 10 paid, so the refund
            should be 10.
        """
        account_cash_rounding_down = self.env['account.cash.rounding'].create({
            'name': 'Rounding down',
            'rounding': 5.0,
            'rounding_method': 'DOWN',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })
        self.pos_config_usd.write({
            'rounding_method': account_cash_rounding_down.id,
            'cash_rounding': True,
        })
        product_tmpl = self.create_product_template('10 Dollars with 10%', 10.0, tax_ids=self.taxes['tax10'].ids)

        self.pos_config_usd.open_ui()
        # order total will be 11.0 with 1.0 taxes excluded, with rounding 10 should be paid
        order = self.create_pos_order(
            [[product_tmpl.product_variant_id]],
            [[self.bank_pm, 5], [self.cash_pm, 5]],
        )
        refund = self.refund_pos_order(order, self.cash_pm, -10)

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
        order_1 = self.create_pos_order(
            [[self.twenty_dollars_with_15_incl.product_variant_id]],
            payments=[[self.credit_pm, 20]],
            customer=parent_partner,
        )
        order_2 = self.create_pos_order(
            [[self.ten_dollars_with_10_incl.product_variant_id]],
            payments=[[self.credit_pm, 10]],
            customer=child_partner,
        )
        self.assertEqual(len(order_1), 1, "Expected 1 order directly on parent partner")
        self.assertEqual(len(order_2), 1, "Expected 1 order directly on child partner")
        self.assertEqual(parent_partner.pos_order_count, 2, "Parent partner should see 2 orders including child’s")
        self.assertEqual(child_partner.pos_order_count, 1, "Child partner should see only their own order")

    def test_backend_order_refund_flow(self):
        """ The purpose of this test is to test the basic flow of
        refunding orders from the backend. More precisely making sure:
        - We do not refund more than the initial order's quantity"""
        self.pos_config_usd.open_ui()

        order = self.create_pos_order(
            [[self.ten_dollars_with_10_incl.product_variant_id]],
            payments=[[self.cash_pm, 10]],
        )

        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                with self.assertRaises(ValidationError, msg="You cannot refund more than the original order."):
                    line.qty = -3

    def test_order_to_invoice_no_tax(self):
        order = self.create_pos_order(
            [
                [self.ten_dollars_no_tax.product_variant_id],
                [self.twenty_dollars_no_tax.product_variant_id],
            ],
            payments=[[self.bank_pm, 30]],
            customer=self.partner_mobt,
        )
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

        self.close_pos_session()

    def test_pos_order_invoice_payment_term(self):
        """ Test that when invoicing a POS order paid with customer account, the partner's payment term is then applied to the invoice. """
        pay_term_30 = self.env.ref('account.account_payment_term_30days')
        partner_a = self.env["res.partner"].create({
            'name': 'APartner',
            'property_payment_term_id': pay_term_30.id,
        })

        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [[self.ten_dollars_no_tax.product_variant_id]],
            payments=[[self.credit_pm, 10.0]],
            customer=partner_a,
            to_invoice=True,
        )

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
        order = self.create_pos_order(
            [[self.twenty_dollars_no_tax.product_variant_id]],
            payments=[
                [self.cash_pm, 10],
                [self.credit_pm, 20],
                [self.cash_pm, -10],
            ],
            customer=self.partner_adgu,
            to_invoice=True,
        )
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

        order = self.create_pos_order(
            [
                [self.ten_dollars_with_10_incl.product_variant_id],
                [self.twenty_dollars_with_10_incl.product_variant_id],
            ],
            payments=[[self.cash_pm, 30]],
            customer=self.partner_jcb,
            to_invoice=True,
        )

        self.assertEqual(order.account_move.amount_residual, 0)

    def test_order_invoiced_by_user_without_accounting_access(self):
        """
            Invoicing an order from the POS must reconcile the invoice with its
            payments even when the salesperson has no accounting access rights.
        """
        pos_user = self.env['res.users'].create({
            'name': 'Salesperson without accounting access',
            'login': 'pos_user_no_accounting',
            'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('point_of_sale.group_pos_user').id,
            ])],
        })

        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [[self.twenty_dollars_with_10_incl.product_variant_id]],
            payments=[[self.cash_pm, 20]],
            customer=self.partner_jcb,
        )

        order.with_user(pos_user).action_pos_order_invoice()

        invoice = order.account_move
        receivable_account = self.partner_jcb.property_account_receivable_id
        invoice_receivable_lines = invoice.line_ids.filtered(lambda line: line.account_id == receivable_account)
        self.assertTrue(all(invoice_receivable_lines.mapped('reconciled')))
        self.assertEqual(invoice.amount_residual, 0)

    def test_order_refund_with_invoice(self):
        """This test make sure that credit notes of pos orders are correctly
           linked to the original invoice."""
        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [[self.twenty_dollars_with_15_incl.product_variant_id]],
            payments=[[self.bank_pm, 20]],
            customer=self.partner_adgu,
            to_invoice=True,
        )
        self.refund_pos_order(order, self.bank_pm, -20)

        self.close_pos_session()
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        credit_notes = self.env['account.move'].search([('move_type', '=', 'out_refund')], order='id desc', limit=1)
        self.assertEqual(credit_notes.ref, "Reversal of: "+invoices.name)
        self.assertEqual(credit_notes.reversed_entry_id.id, invoices.id)

    def test_load_data_omits_pricelist_when_disabled(self):
        """Should not have default_pricelist if use_pricelist is false."""

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        self.pos_config_usd.write({
            'pricelist_id': pricelist.id,
            'use_pricelist': False,
        })
        self.pos_config_usd.open_ui()
        loaded_data = self.pos_config_usd.current_session_id.load_data({'only_records': False})

        self.assertFalse(loaded_data['pos.config']['records'][0]['pricelist_id'], False)

    def test_refund_rounding_backend(self):
        account_cash_rounding_up = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 5.0,
            'rounding_method': 'UP',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })
        self.pos_config_usd.write({
            'rounding_method': account_cash_rounding_up.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        tax_15_excl = self.env['account.tax'].create({'name': 'Tax 15% Excl', 'amount': 15})
        twenty_dollars_with_15_excl = self.create_product_template('20 Dollars with 15%', 20.0, tax_ids=tax_15_excl.ids)
        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [[twenty_dollars_with_15_excl.product_variant_id]],
            payments=[[self.cash_pm, 23.0]],
        )
        refund = self.refund_pos_order(order, self.cash_pm, -23.0)

        self.close_pos_session()
        refund_payment = refund.payment_ids[0]
        self.assertEqual(refund_payment.amount, -25.0)
        self.assertEqual(refund.amount_total, -23.00)
        self.assertEqual(refund.amount_paid, -25.0)

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
        bank_payment_method = self.bank_pm.copy()
        # Also checks that a PoS can be created in a branch company. (test_pos_creation_in_branch)
        sub_pos_config = self.env['pos.config'].with_company(branch).create({
            'name': 'Main',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaises(ValidationError, msg="The points of sale for the payment method Bank must belong to its company."):
            bank_payment_method.write({"config_ids": sub_pos_config.ids})

    def test_change_with_card_only(self):
        """Test that the change is not skipped if order was overpaid only with card"""
        self.pos_config_usd.open_ui()
        self.product.write({'lst_price': 450, 'taxes_id': [Command.set([])]})
        pos_order = self.create_pos_order(
            [[self.product]],
            payments=[[self.bank_pm, 500]],
            customer=self.partner_a,
            to_invoice=True,
            amount_return=-50.0
        )
        self.assertEqual(pos_order.state, 'paid')
        self.assertRecordValues(pos_order.payment_ids.sorted(), [
            {'amount': -50.0, 'payment_method_id': self.cash_pm.id, 'is_change': True},
            {'amount': 500.0, 'payment_method_id': self.bank_pm.id, 'is_change': False},
        ])
        order_account_move = pos_order.account_move
        self.assertEqual(order_account_move.amount_total, pos_order.amount_total)

        payment_term = order_account_move.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        payment_amount = payment_term.mapped('amount_currency')
        self.assertEqual(len(payment_term), 2)
        self.assertEqual(payment_amount, [500.0, -50.0])

    def test_paid_order_synced_twice_no_duplicate_change(self):
        """A paid order that reaches the server twice (e.g. a retried/duplicated
        sync) must not re-create the server-side change payment, nor duplicate its
        lines or regular payments."""
        self.pos_config_usd.open_ui()
        self.product.write({'lst_price': 450, 'taxes_id': [Command.set([])]})
        order_data = self._create_ui_order_data(
            [[self.product]],
            payments=[[self.bank_pm, 500]],
            customer=self.partner_a,
            amount_return=-50.0
        )

        order_id = self.env['pos.order'].sync_from_ui([copy.deepcopy(order_data)])['pos.order'][0]['id']
        order = self.env['pos.order'].browse(order_id)
        self.assertEqual(order.state, 'paid')
        self.assertRecordValues(order.payment_ids.sorted(), [
            {'amount': -50.0, 'payment_method_id': self.cash_pm.id, 'is_change': True},
            {'amount': 500.0, 'payment_method_id': self.bank_pm.id, 'is_change': False},
        ])

        # Re-sync the exact same paid order (duplicate / retried sync).
        self.env['pos.order'].sync_from_ui([copy.deepcopy(order_data)])
        self.assertEqual(len(order.lines), 1, "Re-syncing must not duplicate the order lines.")
        self.assertRecordValues(order.payment_ids.sorted(), [
            {'amount': -50.0, 'payment_method_id': self.cash_pm.id, 'is_change': True},
            {'amount': 500.0, 'payment_method_id': self.bank_pm.id, 'is_change': False},
        ])

    def test_paid_order_resync_replays_payment_deletion(self):
        """Editing the payments of an already paid order and syncing it twice must
        be idempotent: replaying a delete command for a payment that the first sync
        already removed must not raise MissingError nor duplicate the new payment."""
        self.pos_config_usd.open_ui()
        self.product.write({'lst_price': 450, 'taxes_id': [Command.set([])]})
        order_data = self._create_ui_order_data(
            [[self.product]],
            payments=[[self.cash_pm, 450]],
            customer=self.partner_a
        )
        order_id = self.env['pos.order'].sync_from_ui([copy.deepcopy(order_data)])['pos.order'][0]['id']
        order = self.env['pos.order'].browse(order_id)
        cash_payment = order.payment_ids
        self.assertEqual(len(cash_payment), 1)

        # The cashier removes the cash payment and pays with the bank instead.
        edit_data = copy.deepcopy(order_data)
        edit_data['payment_ids'] = [
            [2, cash_payment.id],
            [0, 0, {
                'amount': 450,
                'name': fields.Datetime.to_string(fields.Datetime.now()),
                'payment_method_id': self.bank_pm.id,
                'uuid': 'pay-bank-22346-123-1234',
            }],
        ]

        # First edit-sync applies the change.
        self.env['pos.order'].sync_from_ui([copy.deepcopy(edit_data)])
        self.assertFalse(cash_payment.exists(), "The cash payment should have been removed.")
        self.assertRecordValues(order.payment_ids, [
            {'amount': 450.0, 'payment_method_id': self.bank_pm.id},
        ])

        # The same edit synced again replays the now stale [2, id] delete command:
        # it must be skipped silently instead of raising MissingError.
        self.env['pos.order'].sync_from_ui([copy.deepcopy(edit_data)])
        self.assertRecordValues(order.payment_ids, [
            {'amount': 450.0, 'payment_method_id': self.bank_pm.id},
        ])

    def test_refund_qty_refund_cancel(self):
        """
        Test the refunded qty of an order, when the refund order has been cancelled
        """

        self.product.write({'lst_price': 100, 'taxes_id': [Command.set([])]})
        order = self.create_pos_order(
            [[self.product]],
            payments=[[self.cash_pm, 100]],
        )

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
        order = self.create_pos_order(
            [[self.product]],
            payments=[],
            state='draft',
            preset_time=fields.Datetime.now() - timedelta(days=2),
        )
        order.cancel_order_from_pos()
        self.assertEqual(order.state, 'cancel')

    def test_pos_order_partner_bank_id(self):
        self.pos_config_usd.open_ui()
        # Case 1: journal bank allows out payment
        allowed_bank = self.env["res.partner.bank"].create({
            "account_number": "FR7612345678901234567890123",
            "partner_id": self.company.partner_id.id,
            "bank_name": "Test Bank",
            "allow_out_payment": True,
        })
        self.cash_pm.journal_id.bank_account_id = allowed_bank

        order = self.create_pos_order(
            [[self.product]],
            payments=[[self.cash_pm, 23]],
            customer=self.partner,
            to_invoice=True,
        )
        invoice = order.account_move
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
        self.cash_pm.journal_id.bank_account_id = blocked_bank
        order = self.create_pos_order(
            [[self.product]],
            payments=[[self.cash_pm, 23]],
            customer=self.partner,
            to_invoice=True,
        )
        invoice = order.account_move
        self.assertNotEqual(
            invoice.partner_bank_id.id,
            blocked_bank.id,
            "Invoice should not use journal bank account when not allowed."
        )

    def test_invoice_rounding_overpaid_backend(self):
        rounding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 0.05,
            'rounding_method': 'UP',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })

        product = self.create_product_template('Product Test', 149.99).product_variant_id

        self.pos_config_usd.write({
            'rounding_method': rounding_method.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })

        self.pos_config_usd.open_ui()
        pos_order = self.create_pos_order(
            [[product]],
            payments=[[self.cash_pm, 100], [self.bank_pm, 50]],
            customer=self.partner,
        )
        self.close_pos_session()

        pos_order.action_pos_order_invoice()
        self.assertEqual(pos_order.state, 'done')

    def test_search_order_ids(self):
        """ Test if the orders from other configs are excluded in search_order_ids """
        other_pos_config = self.env['pos.config'].create({
            'name': 'Other POS',
            'payment_method_ids': [Command.set(self.bank_pm.ids)],
        })
        self.pos_config_usd.open_ui()
        other_pos_config.open_ui()
        paid_order_1, paid_order_2 = self.create_orders([
            {
                'lines': [[self.ten_dollars_no_tax.product_variant_id]],
                'payments': [[self.bank_pm, 10]],
                'customer': self.partner,
                'config': config,
            }
            for config in (self.pos_config_usd, other_pos_config)
        ]).values()
        cancelled_order = self.create_pos_order(
            [[self.ten_dollars_no_tax.product_variant_id]],
            payments=[],
            customer=self.partner,
            config=other_pos_config,
            state='draft',
        )
        cancelled_order.cancel_order_from_pos()

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

        order_data = self._create_ui_order_data(
            [[product, 1, 0, {'price_unit': 6, 'tax_ids': [Command.set([])]}]],
            payments=[],
            customer=self.partner,
            config=config,
            state='draft',
        )
        order = self.env['pos.order'].with_user(user).with_company(branch).create(order_data)

        order_line = order.lines[0]
        self.env.invalidate_all()
        order_line.with_user(user).with_company(branch)._compute_total_cost()

    def test_delete_res_partner_linked_to_pos_order(self):
        """ Test that a partner linked to a pos order cannot be deleted. """
        partner = self.env['res.partner'].create({
            'name': 'Partner test',
        })
        self.create_pos_order(
            [[self.product, 1, 0, {'price_unit': 450, 'tax_ids': [Command.set([])]}]],
            payments=[],
            customer=partner,
            state='draft',
        )

        with self.assertRaises(ValidationError, msg='You cannot delete a customer that has point of sales orders. You can archive it instead.'):
            partner.unlink()

    def test_draft_orders_products_loading(self):
        """ Test that products are correctly loaded when limited product loading is enabled and there are draft orders. """
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 1)
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        products = (self.ten_dollars_no_tax | self.twenty_dollars_no_tax).product_variant_id
        self.create_orders([
            {'lines': [[product]], 'payments': [], 'state': 'draft'}
            for product in products
        ])

        data = current_session.with_context(pos_limited_loading=True).load_data({'only_records': True})
        loaded_product_ids = [p['id'] for p in data['product.product']]
        for product in products:
            self.assertIn(product.id, loaded_product_ids)

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
        order = self.create_pos_order(
            [[self.product, 1, 0, {'price_unit': 750, 'tax_ids': [Command.set([])]}]],
            payments=[[self.bank_pm, 750]],
        )

        self.assertEqual(order.name, f"/AA - {order.pos_reference.split('-')[-1]} - 1.B")

    def test_create_journal_and_payment_methods_bank_journal_explicit_company_currency(self):
        """A bank journal whose currency is explicitly set to the company currency
        (instead of left empty) must still be found and used, not treated as a
        foreign-currency journal."""
        self.env['pos.payment.method'].search([]).write({'active': False})
        self.company_data['default_journal_bank'].currency_id = self.company.currency_id
        _, pm_ids = self.pos_config_usd._create_journal_and_payment_methods()
        bank_pm = self.env['pos.payment.method'].browse(pm_ids).filtered(lambda pm: pm.name == 'Card')
        self.assertEqual(bank_pm.journal_id, self.company_data['default_journal_bank'])

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
        order = self.create_pos_order(
            [[self.product]],
            payments=[],
            state='draft',
        )
        sync_from_ui_values = self._create_ui_order_data(
            [[self.product, 2, 0, {'uuid': order.lines.uuid}]],
            payments=[],
            state='draft',
            uuid=order.uuid,
            id=order.id,
            access_token=order.access_token,
        )
        self.env['pos.order'].sync_from_ui([sync_from_ui_values])
        self.assertEqual(len(order.lines), 1, "Two lines with the same UUID were created")
        self.assertEqual(order.lines[0].qty, 2, "The quantity of the line should have been updated to 2")

    def test_manual_refund_negative_qty_invoice_creates_credit_note(self):
        """Invoicing a POS order created with negative qty (manual refund, no Refund action)
        must create a credit note (RINV/out_refund), not a customer invoice (INV)."""
        self.pos_config_usd.open_ui()

        # Create an order with negative qty only (no Refund action → is_refund stays False)
        order = self.create_pos_order(
            [[self.ten_dollars_no_tax.product_variant_id, -1]],
            payments=[[self.cash_pm, -10]],
            customer=self.partner_mobt,
        )

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

    def test_reversal_move_tax_base_amount_sign(self):
        """When a POS order is invoiced after its session is closed, the reversal misc entry
        created to unwind the corresponding portion of the closing entry must have consistent
        signs on `balance` and `tax_base_amount` for every tax line. Otherwise any downstream
        report reading `tax_base_amount` directly (Audit view, journal items XLSX export, etc.)
        shows a base amount signed for the opposite direction than the tax leg, which is
        confusing and, for tax returns computed from `tax_base_amount`, incorrect.
        """
        tax_15_excl = self.env['account.tax'].create({'name': 'Tax 15% Excl', 'amount': 15})
        twenty_dollars_with_15_excl = self.create_product_template('20 Dollars with 15%', 20.0, tax_ids=tax_15_excl.ids)
        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [[twenty_dollars_with_15_excl.product_variant_id]],
            payments=[[self.bank_pm, 23]],
            to_invoice=False,
        )
        self.close_pos_session()

        order.partner_id = self.partner_jcb
        order.action_pos_order_invoice()

        reversal_move = self.env['account.move'].search(
            [('reversed_pos_order_id', '=', order.id)], limit=1
        )
        self.assertTrue(reversal_move, "Invoicing after session close should create a reversal misc move")

        tax_lines = reversal_move.line_ids.filtered(lambda l: l.display_type == 'tax')
        self.assertTrue(tax_lines, "Reversal move should have at least one tax line")

        for tax_line in tax_lines:
            self.assertNotEqual(tax_line.balance, 0.0)
            self.assertNotEqual(tax_line.tax_base_amount, 0.0)
            self.assertEqual(
                tax_line.balance > 0,
                tax_line.tax_base_amount > 0,
                "Reversal tax line %s: balance=%s but tax_base_amount=%s (signs must agree)" % (
                    tax_line.name, tax_line.balance, tax_line.tax_base_amount,
                ),
            )

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
        data = session.load_data({'only_records': True})
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

        data = session.with_context(pos_last_server_date=last_server_date).load_data({'only_records': True})
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

        order = self.create_pos_order(
            [[self.product, 1, 0, {'price_unit': 750, 'tax_ids': [Command.set([])]}]],
            payments=[[self.bank_pm, 750]],
        )

        # Verify order name contains interpolated year and month with static parts
        current_year = fields.Datetime.now().year
        current_month = fields.Datetime.now().strftime('%m')

        self.assertIn(f'POS-{current_year}', order.name,
            f"Order name should contain 'POS-{current_year}', got: {order.name}")
        self.assertIn(f'-{current_month}', order.name,
            f"Order name should contain '-{current_month}', got: {order.name}")

    def test_order_edit_logs(self):
        self.pos_config_usd.open_ui()
        order = self.create_pos_order(
            [
                [self.ten_dollars_no_tax.product_variant_id, 2],
                [self.twenty_dollars_no_tax.product_variant_id],
            ],
            payments=[],
            state='draft',
        )
        order.lines[0].qty = 1
        order.lines[1].unlink()
        logged_messages = order.message_ids.mapped('body')
        self.assertTrue(order.is_edited)
        self.assertEqual(len(logged_messages), 2)
        self.assertIn('Twenty dollars no tax: Deleted line (quantity: 1.0)', logged_messages[0])
        self.assertIn('Ten dollars no tax: Ordered quantity: 2.0 → 1', logged_messages[1])

    def test_cash_in_out_has_no_partner(self):
        """The cashier is not the counterpart of a cash move: it must not be set as
        partner on the statement line nor on its journal items."""
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        session.set_opening_control(0, False)
        session.try_cash_in_out('in', 10, 'Float', self.env.user.partner_id.id)

        cash_move = session.bank_statement_line_ids
        self.assertFalse(cash_move.partner_id)
        self.assertFalse(cash_move.move_id.line_ids.partner_id)
        self.assertEqual(session.get_cash_in_out_list()[0]['cashier_name'], self.env.user.name)

    def test_refund_of_a_global_discount(self):
        """ The global discount line pins in 'extra_tax_data' base and tax amounts that cannot be
        recomputed from its price. The UI does not refund that line, it applies the discount again
        on the refund order, where the refunded lines are negative and the discount is therefore
        positive. Those pinned amounts have to be used as they are on both orders, otherwise the
        totals of an order and of its refund do not cancel each other.
        """
        AccountTax = self.env['account.tax']
        company = self.env.company
        tax = AccountTax.create({'name': 'Tax 20%', 'amount': 20})
        product = self.env['product.product'].create({
            'name': 'Product 2.12',
            'available_in_pos': True,
            'lst_price': 2.12,
            'taxes_id': [Command.set(tax.ids)],
        })

        def discount_line(quantity):
            """ The values the UI stores for a 10% global discount on 'quantity' x that product. """
            base_lines = [AccountTax._prepare_base_line_for_taxes_computation(
                None, product_id=product, tax_ids=product.taxes_id, price_unit=product.lst_price,
                quantity=quantity, currency_id=company.currency_id, rate=1.0,
            )]
            AccountTax._add_tax_details_in_base_lines(base_lines, company)
            AccountTax._round_base_lines_tax_details(base_lines, company)
            line = AccountTax._prepare_global_discount_lines(base_lines, company, 'percent', 10.0)[0]
            return [
                product,
                line['quantity'],
                0.0,
                {
                    'price_unit': company.currency_id.round(line['price_unit']),
                    'extra_tax_data': AccountTax._export_base_line_extra_tax_data(line),
                },
            ]

        self.pos_config_usd.open_ui()
        order, refund = (
            self.create_pos_order(
                [[product, quantity], discount_line(quantity)],
                payments=[],
                state='draft',
            )
            for quantity in (2, -2)
        )
        self.assertAlmostEqual(
            order.amount_tax + refund.amount_tax, 0.0,
            msg="The taxes of an order and of its refund should cancel each other.",
        )
        self.assertAlmostEqual(
            order.amount_total + refund.amount_total, 0.0,
            msg="The totals of an order and of its refund should cancel each other.",
        )

    def test_available_children_categories(self):
        parent_categ = self.env['pos.category'].create({
            'name': 'Parent Category',
        })
        children_categs = self.env['pos.category'].create([{
            'name': 'Child Category 1',
            'parent_id': parent_categ.id,
        }, {
            'name': 'Child Category 2',
            'parent_id': parent_categ.id,
        }])
        self.env['product.product'].create([{
            'name': 'parent product',
            'pos_categ_ids': [(6, 0, [parent_categ.id])],
            'available_in_pos': True,
        }, {
            'name': 'child product 1',
            'pos_categ_ids': [(6, 0, [parent_categ.id, children_categs[0].id])],
            'available_in_pos': True,
        }, {
            'name': 'child product 2',
            'pos_categ_ids': [(6, 0, [parent_categ.id, children_categs[1].id])],
            'available_in_pos': True,
        }])
        self.pos_config_usd.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [parent_categ.id, children_categs[1].id])],
        })
        self.pos_config_usd.open_ui()
        loaded_data = self.pos_config_usd.current_session_id.load_data({'only_records': True})
        category_id = [category['id'] for category in loaded_data['pos.category']]
        self.assertNotIn(children_categs[0].id, category_id, "Child category is unavailable and shouldn't appear in the POS")
        self.assertIn(children_categs[1].id, category_id, "Child category is available and should appear in the POS")

    def test_available_product_uom_ids(self):
        # Making sure that all of the non-special products that are included in the `load_data` are the ones created in this method.
        self.env['product.template'].search([]).write({'is_favorite': False})

        self.env['ir.config_parameter'].sudo().set_str('point_of_sale.limited_product_count', '2')
        uom = self.env['uom.uom'].create({
            'name': 'Random UOM',
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        product_one, product_two, product_three = self.env['product.product'].create([{
            'name': "product_one",
            'available_in_pos': True,
            'is_favorite': True,
        },
        {
            'name': "product_two",
            'available_in_pos': True,
            'is_favorite': True,
        },
        {
            'name': "product_three",
            'available_in_pos': True,
        }])

        _, _, product_uom_three = self.env['product.uom'].create([{
            'barcode': "product_one_barcode",
            'uom_id': uom.id,
            'product_id': product_one.id,
        },
        {
            'barcode': "product_two_barcode",
            'uom_id': uom.id,
            'product_id': product_two.id,
        },
        {
            'barcode': "product_three_barcode",
            'uom_id': uom.id,
            'product_id': product_three.id,
        },
        ])

        self.env['product.template'].flush_model()
        self.pos_config_usd.open_ui()
        loaded_data = self.pos_config_usd.current_session_id.load_data({'only_records': True})
        loaded_product_uoms = [loaded_product_uom['id'] for loaded_product_uom in loaded_data['product.uom']]

        self.assertNotIn(product_uom_three.id, loaded_product_uoms, f"Product UOM {product_uom_three} shouldn't be loaded as its product {product_three} is not included in the results")

    def test_kpi_invoiced_pos_orders_counted(self):
        context = {
            'start_datetime': datetime.now() - relativedelta(days=1),
            'end_datetime': datetime.now() + relativedelta(days=1),
        }
        digest = self.env['digest.digest'].with_context(context).create([{
            'name': 'Digest 1',
            'company_id': self.env.company.id,
            'kpi_mail_message_total': True,
            'kpi_res_users_connected': True,
            'periodicity': 'daily',
        }])
        self.create_orders([
            {'lines': [[self.ten_dollars_with_10_incl.product_variant_id]], 'payments': [[self.bank_pm, 10]]},
            {'lines': [[self.ten_dollars_with_10_incl.product_variant_id]], 'payments': [[self.bank_pm, 10]], 'customer': self.partner, 'to_invoice': True},
        ])
        self.close_pos_session()

        self.assertEqual(digest.kpi_pos_total_value, 20.0)
