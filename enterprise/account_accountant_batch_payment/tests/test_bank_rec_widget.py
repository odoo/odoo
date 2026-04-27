# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo import Command
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged, TransactionCase


class CommonAccountingInstalled(TransactionCase):
    module = 'accounting'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.registry['account.move'], '_get_invoice_in_payment_state', lambda self: 'in_payment')
        cls.payment_method_line = cls.company_data['default_journal_bank'].inbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'batch_payment')
        cls.early_payment_term = cls.env['account.payment.term'].create({
            'name': "early_payment_term",
            'company_id': cls.company_data['company'].id,
            'discount_percentage': 2,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

    def _register_payment(self, invoice, **kwargs):
        return self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_method_line_id': self.payment_method_line.id,
            **kwargs,
        })._create_payments()


class CommonInvoicingOnly(TransactionCase):
    module = 'invoicing_only'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.registry['account.move'], '_get_invoice_in_payment_state', lambda self: 'paid')
        # When accounting is not installed, outstanding accounts are created and referenced only by xmlid
        xml_id = f"account.{cls.env.company.id}_account_journal_payment_debit_account_id"
        if not cls.env.ref(xml_id, raise_if_not_found=False):
            cls.env['account.account']._load_records([
                {
                    'xml_id': xml_id,
                    'values': {
                        'name': "Outstanding Receipts",
                        'prefix': '123456',
                        'code_digits': 6,
                        'account_type': 'asset_current',
                        'reconcile': True,
                    },
                    'noupdate': True,
                }
            ])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithoutEntry(CommonAccountingInstalled, TestBankRecWidgetCommon):
    def test_state_changes(self):
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_line_ids=[{'price_unit': 1000.0, 'tax_ids': []}],
        )
        invoice = inv_line.move_id
        invoice_payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
        })._create_payments()
        from_scratch_payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 1000,
        })
        from_scratch_payment.action_post()
        for payment, expect_reconcile in [(invoice_payment, True), (from_scratch_payment, self.module == 'invoicing_only')]:
            self.assertFalse(payment.move_id and self.module == 'accounting')
            batch = self.env['account.batch.payment'].create({
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_ids': [Command.set(payment.ids)],
                'payment_method_id': self.payment_method_line.payment_method_id.id,
            })
            batch.validate_batch()
            self.assertIn(payment.state, self.env['account.batch.payment']._valid_payment_states())
            self.assertEqual(payment.is_sent, True)
            self.assertRecordValues(batch, [{'state': 'sent'}])

            st_line = self._create_st_line(1000.0, payment_ref=batch.name, partner_id=self.partner_a.id)
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_add_new_batch_payments(batch)
            self.assertRecordValues(wizard.line_ids, [
                # pylint: disable=C0326
                {'flag': 'liquidity',       'balance':  1000.0},
                {'flag': 'new_batch',       'balance': -1000.0},
            ])
            wizard._action_validate()

            if self.module == 'accounting':
                counterpart_account = self.partner_a.property_account_receivable_id
            else:
                counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': counterpart_account.id,                   'balance': -1000.0, 'reconciled': expect_reconcile},
                {'account_id': st_line.journal_id.default_account_id.id, 'balance':  1000.0, 'reconciled': False},
            ])
            self.assertRecordValues(payment, [{
                'state': 'paid',
                'is_sent': True,
            }])
            self.assertRecordValues(batch, [{'state': 'reconciled'}])

            if payment == invoice_payment:
                wizard._js_action_reset()
                self.assertRecordValues(batch, [{'state': 'sent'}])
                if self.module == 'accounting':
                    wizard._action_add_new_amls(inv_line)
                else:
                    aml = payment.move_id.line_ids.filtered(lambda x: x.account_id.account_type != 'asset_receivable')
                    wizard._action_add_new_amls(aml)
                self.assertRecordValues(wizard.line_ids, [
                    {'flag': 'liquidity',       'balance':  1000.0},
                    {'flag': 'new_aml',         'balance': -1000.0},
                ])
                wizard._action_validate()
                self.assertRecordValues(batch, [{'state': 'reconciled'}])

    def test_reset_batch(self):
        payment_state = 'paid' if self.module == 'invoicing_only' else 'in_process'
        invoice_payment_state = 'paid' if self.module == 'invoicing_only' else 'in_payment'

        # Setup: one invoice with 2 payments, each in a batch, with a matching statement line
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[20.0], post=True)
        payment1 = self._register_payment(invoice, amount=5.0)
        payment2 = self._register_payment(invoice, amount=15.0)

        batch1 = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment1.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch1.validate_batch()
        batch2 = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment2.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch2.validate_batch()

        st_line1 = self._create_st_line(5.0, payment_ref=batch1.name, partner_id=self.partner_a.id)
        st_line2 = self._create_st_line(15.0, payment_ref=batch1.name, partner_id=self.partner_a.id)

        # Check initial state
        self.assertRecordValues(payment1 + payment2, [
            {'state': payment_state, 'is_matched': False},
            {'state': payment_state, 'is_matched': False},
        ])
        self.assertEqual(invoice.payment_state, invoice_payment_state)
        self.assertRecordValues(batch1 + batch2, [{'state': 'sent'}, {'state': 'sent'}])

        # Match the first batch and make sure the states are updated
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line1.id).new({})
        wizard._action_add_new_batch_payments(batch1)
        wizard._action_validate()
        self.assertRecordValues(payment1 + payment2, [
            {'state': 'paid', 'is_matched': True},
            {'state': payment_state, 'is_matched': False},
        ])
        self.assertEqual(invoice.payment_state, invoice_payment_state)
        self.assertRecordValues(batch1 + batch2, [{'state': 'reconciled'}, {'state': 'sent'}])

        # Match the second batch and make sure the states are updated
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line2.id).new({})
        wizard._action_add_new_batch_payments(batch2)
        wizard._action_validate()
        self.assertRecordValues(payment1 + payment2, [
            {'state': 'paid', 'is_matched': True},
            {'state': 'paid', 'is_matched': True},
        ])
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertRecordValues(batch1 + batch2, [{'state': 'reconciled'}, {'state': 'reconciled'}])

        # Reset and check that we are back to the state before we matched the batch
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line1.id).new({})
        wizard._js_action_reset()
        self.assertRecordValues(payment1 + payment2, [
            {'state': payment_state, 'is_matched': False},
            {'state': 'paid', 'is_matched': True},
        ])
        self.assertEqual(invoice.payment_state, invoice_payment_state)
        self.assertRecordValues(batch1 + batch2, [{'state': 'sent'}, {'state': 'reconciled'}])

    def test_writeoff(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
        })._create_payments()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(900.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   900.0},
            {'flag': 'new_batch',       'balance': -1000.0},
            {'flag': 'auto_balance',    'balance':   100.0},
        ])
        line = wizard.line_ids.filtered(lambda l: l.flag == 'auto_balance')
        wizard._js_action_mount_line_in_edit(line.index)
        wizard._js_action_line_set_partner_receivable_account(line.index)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   900.0},
            {'flag': 'new_batch',       'balance': -1000.0},
            {'flag': 'manual',          'balance':   100.0},
        ])
        wizard._action_validate()

        if self.module == 'accounting':
            counterpart_account = self.partner_a.property_account_receivable_id
        else:
            counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')

        self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
            {'account_id': counterpart_account.id,                           'balance': -1000.0, 'reconciled': True},
            {'account_id': self.partner_a.property_account_receivable_id.id, 'balance':   100.0, 'reconciled': False},
            {'account_id': st_line.journal_id.default_account_id.id,         'balance':   900.0, 'reconciled': False},
        ])

    def test_multiple_exchange_diffs_in_batch(self):
        if self.module == 'invoicing_only':
            self.skipTest('Already tested in TestBankRecWidgetWithEntry')
        # Create a statement line when the currency rate is 1 USD == 2 EUR == 4 CAD
        st_line = self._create_st_line(
            1000.0,
            partner_id=self.partner_a.id,
            date='2017-01-01'
        )
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_line_ids=[{'price_unit': 5000.0, 'tax_ids': []}],
        )
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 100.0,
        })
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 200.0,
        })
        # Payment when 1 USD == 3 EUR
        payment_eur_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 240.0,
        })
        # Payment when 1 USD == 6 CAD
        payment_cad_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency_2.id,
            'amount': 300.0,
        })
        payments = payment_eur_gain_diff + payment_eur_gain_diff_2 + payment_eur_loss_diff + payment_cad_loss_diff
        payments.action_post()

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'new_aml',         'balance': -1000.0},
        ])

        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_batch',       'amount_currency': -430.0,     'balance': -430.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  150.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  -40.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  -25.0},
        ])

        wizard._js_action_validate()
        self.assertRecordValues(st_line.move_id.line_ids, [
            # pylint: disable=C0326
            # ruff: noqa: E221
            {'balance': -100.0, 'amount_currency': -100.0, 'amount_residual': -100.0},
            {'balance': -200.0, 'amount_currency': -200.0, 'amount_residual': -200.0},
            {'balance':  -80.0, 'amount_currency': -240.0, 'amount_residual':  -80.0},
            {'balance':  -50.0, 'amount_currency': -300.0, 'amount_residual':  -50.0},
            {'balance':  150.0, 'amount_currency':    0.0, 'amount_residual':    0.0},
            {'balance':  -40.0, 'amount_currency':    0.0, 'amount_residual':    0.0},
            {'balance':  -25.0, 'amount_currency':    0.0, 'amount_residual':    0.0},
            {'balance': 1000.0, 'amount_currency': 1000.0, 'amount_residual': 1000.0},
            {'balance': -655.0, 'amount_currency': -655.0, 'amount_residual':    0.0},
        ])

        reconciled = st_line.move_id.line_ids.matched_debit_ids.debit_move_id | st_line.move_id.line_ids.matched_credit_ids.credit_move_id
        self.assertRecordValues(reconciled, [
            {'balance':   5000.0, 'amount_currency':   5000.0, 'amount_residual':   4345.0},
        ])

    def test_invoice_partial_batch_payment(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
            'amount': 500.0,
        })._create_payments()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(500.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity', 'balance':  500.0},
            {'flag': 'new_batch', 'balance': -500.0},
        ])
        wizard._action_validate()

        if self.module == 'accounting':
            counterpart_account = self.partner_a.property_account_receivable_id
        else:
            counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')

        self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
            {'account_id': counterpart_account.id,                   'balance': -500.0, 'reconciled': True},
            {'account_id': st_line.journal_id.default_account_id.id, 'balance':  500.0, 'reconciled': False},
        ])
        self.assertEqual(invoice.amount_residual, 500.0)
        self.assertEqual(batch.amount_residual, 0.0)

    def test_batch_with_cancelled_or_rejected_payments(self):
        payment_1 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 100.0,
        })
        payment_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 200.0,
        })
        payment_3 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 300.0,
        })
        payments = payment_1 + payment_2 + payment_3
        payments.action_post()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()
        self.assertEqual(batch.amount_residual, 600.0)
        # cancel first payment
        payment_1.action_cancel()
        # reject second payment
        payment_2.action_reject()
        self.assertEqual(batch.amount_residual, 300.0)

        st_line = self._create_st_line(300.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        wizard._action_validate()
        self.assertEqual(batch.amount_residual, 0.0)
        self.assertEqual(batch.state, 'reconciled')
        self.assertEqual(payment_1.state, 'canceled')
        self.assertEqual(payment_2.state, 'rejected')
        self.assertEqual(payment_3.state, 'paid')

    def test_match_batch_partial_payments(self):
        """ Test reconcile a batch of partial payments with the corresponding statement """
        payments = self.env['account.payment']
        invoice1 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10.0], post=True)
        payments |= self._register_payment(invoice1, amount=2.0)
        payments |= self._register_payment(invoice1, amount=2.0)
        invoice2 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=True)
        payments |= self._register_payment(invoice2, amount=20.0)
        invoice3 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        other_account = self.partner_a.property_account_receivable_id.copy()
        invoice3.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id = other_account
        payments |= self._register_payment(invoice3, amount=200.0)
        invoice4 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10000.0], post=True)
        payments |= self._register_payment(invoice4, amount=20000.0)

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(20224.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   20224.0},
            {'flag': 'new_batch',       'balance':  -20224.0},
        ])
        wizard._action_validate()
        self.assertRecordValues(payments, [{'state': 'paid'}] * 5)
        self.assertRecordValues(invoice1 + invoice2 + invoice3 + invoice4, [
            {'amount_residual':   6.0},
            {'amount_residual':  80.0},
            {'amount_residual': 800.0},
            {'amount_residual':   0.0},
        ])

        bank_account = st_line.journal_id.default_account_id
        if self.module == 'accounting':
            receivable = self.partner_a.property_account_receivable_id
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': receivable.id,    'balance': -20000.0, 'amount_residual': -10000.0},
                {'account_id': other_account.id, 'balance':   -200.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':    -20.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': bank_account.id,  'balance':  20224.0, 'amount_residual':  20224.0},
            ])
        else:
            outstanding = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': outstanding.id,   'balance': -20000.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':   -200.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':    -20.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': bank_account.id,  'balance':  20224.0, 'amount_residual':  20224.0},
            ])

    def test_bills_match_batch_payment(self):
        """ Test reconcile a batch of bill payments (containing a grouped payment) with the corresponding statement """
        self.outbound_payment_method_line.payment_account_id = False
        bill1 = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[10.0], post=True)
        bill2 = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[100.0], post=True)
        bill3 = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        # create a grouped payment for bill1 and bill2
        active_ids = (bill1 + bill2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 110.0,
            'group_payment': True,
            'payment_difference_handling': 'open',
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()
        # create a simple payment for bill3
        payments |= self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill3.ids).create({
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()
        # create a batch payment with both payments
        batch = self.env['account.batch.payment'].create({
            'batch_type': 'outbound',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.outbound_payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(-1110.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        wizard._action_validate()
        self.assertRecordValues(payments, [{'state': 'paid'}] * 2)
        self.assertRecordValues(bill1 + bill2 + bill3, [
            {'amount_residual':   0.0},
            {'amount_residual':   0.0},
            {'amount_residual':   0.0},
        ])

    def test_batch_reconciliation_exchange_diff(self):
        self.env['res.currency.rate'].create({
            'name': '2017-02-01',
            'rate': 4.00,
            'currency_id': self.other_currency.id,
            'company_id': self.company_data['company'].id,
        })

        other_currency_journal = self.env['account.journal'].create({
            'name': 'Bank other currency',
            'code': 'OTR',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
            'currency_id': self.other_currency.id,
        })

        # Create a statement line when the currency rate is 1 USD == 2 EUR
        st_line = self._create_st_line(
            -1130.0,
            partner_id=self.partner_a.id,
            date='2017-01-01',
            journal_id=other_currency_journal.id,
        )
        bill = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[1130.0], post=True, currency=self.other_currency)
        # Create a statement line when the currency rate is 1 USD == 3 EUR
        payment_eur = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'amount': 1130.0,
            'payment_date': '2016-01-01',
            'journal_id': other_currency_journal.id,
            'currency_id': self.other_currency.id,
        })._create_payments()

        payment_eur.action_post()
        batch = self.env['account.batch.payment'].create({
            'journal_id': other_currency_journal.id,
            'payment_ids': [Command.set(payment_eur.ids)],
            'batch_type': 'outbound',
            'payment_method_id': self.outbound_payment_method_line.payment_method_id.id,
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': -565.0},
            {'flag': 'new_batch',       'balance':  376.67},
            {'flag': 'exchange_diff',   'balance': 188.32999999999998},
        ])
        # Reconcile when the currency rate is 1 USD == 4 EUR
        wizard._action_validate()
        if self.module == 'accounting':
            self.assertRecordValues(st_line.move_id.line_ids, [
                {'amount_currency':  1130.0, 'amount_residual':    0.0, 'balance':  376.67},
                {'amount_currency':     0.0, 'amount_residual':    0.0, 'balance':  188.33},
                {'amount_currency': -1130.0, 'amount_residual': -565.0, 'balance': -565.00},
            ])
        else:
            self.assertRecordValues(st_line.move_id.line_ids, [
                {'amount_currency': -1130.0, 'amount_residual': -565.0, 'balance': -565.00},
                {'amount_currency':  1130.0, 'amount_residual':    0.0, 'balance':  565.00},
            ])

    def test_batch_reconciliation_currency_rate_change(self):
        """ Ensure that in case currency rate is changed midday, the reconciliation of
        a batch payment with a bank statement will work as expected.
        """
        other_currency_journal = self.env['account.journal'].create({
            'name': 'Bank other currency',
            'code': 'OTR',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
            'currency_id': self.other_currency.id,
        })

        # Create a bill for 200EUR when 1USD = 2EUR
        self.env['res.currency.rate'].create({
            'name': '2017-02-01',
            'rate': 2,
            'currency_id': self.other_currency.id,
            'company_id': self.company_data['company'].id,
        })
        bill = self.init_invoice(
            'in_invoice',
            partner=self.partner_a,
            amounts=[200.0],
            post=True,
            currency=self.other_currency,
            invoice_date="2017-02-01",
        )

        # Create a payment for 200EUR when 1USD = 2EUR, for the day after
        payment_eur = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'amount': 200.0,
            'payment_date': '2017-02-02',
            'journal_id': other_currency_journal.id,
            'currency_id': self.other_currency.id,
        })._create_payments()

        # ensure the amount in company currency is computed before we create the new exchange rate
        self.assertEqual(payment_eur.amount_company_currency_signed, -100.0)

        payment_eur.action_post()
        batch = self.env['account.batch.payment'].create({
            'journal_id': other_currency_journal.id,
            'payment_ids': [Command.set(payment_eur.ids)],
            'batch_type': 'outbound',
            'payment_method_id': self.outbound_payment_method_line.payment_method_id.id,
        })
        # On the day after we know that the exchange rate is now 1USD = 4 EUR
        self.env['res.currency.rate'].create({
            'name': '2017-02-02',
            'rate': 4,
            'currency_id': self.other_currency.id,
            'company_id': self.company_data['company'].id,
        })

        st_line = self._create_st_line(
            -200.0,
            partner_id=self.partner_a.id,
            date='2017-02-02',
            journal_id=other_currency_journal.id,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            {'flag': 'liquidity',     'balance': -50},
            {'flag': 'new_batch',     'balance': 100},
            {'flag': 'exchange_diff', 'balance': -50},
        ])
        # Reconcile when the currency rate is 1 USD == 4 EUR
        wizard._action_validate()
        if self.module == 'accounting':
            self.assertRecordValues(st_line.move_id.line_ids, [
                {'amount_currency':  200.0,   'amount_residual':   0.0,   'balance': 100.0},
                {'amount_currency':    0.0,   'amount_residual':   0.0,   'balance': -50.0},
                {'amount_currency': -200.0,   'amount_residual': -50.0,   'balance': -50.0},
            ])
        else:
            self.assertRecordValues(st_line.move_id.line_ids, [
                {'amount_currency': -200.0,   'amount_residual': -50.0,   'balance': -50.0},
                {'amount_currency':  200.0,   'amount_residual':   0.0,   'balance':  50.0},
            ])

    def test_match_batch_with_installments_and_epd(self):
        invoice_installments_1 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=False)
        invoice_installments_2 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[200.0], post=False)
        invoice_epd = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=False)
        (invoice_installments_1 + invoice_installments_2).invoice_payment_term_id = self.pay_terms_b  # Pay 30% now, the rest later
        invoice_epd.invoice_payment_term_id = self.early_payment_term
        invoices = invoice_epd + invoice_installments_1 + invoice_installments_2
        invoices.action_post()

        payments = self._register_payment(invoices, payment_date=invoice_installments_1.invoice_date)
        self.assertEqual(sum(payments.mapped('amount')), 188.0)

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(188.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        if self.module == 'accounting':
            self.assertTrue(wizard._check_for_epd(batch))

            epd_line = wizard.line_ids.filtered(lambda line: line.flag == 'early_payment')
            self.assertTrue(epd_line)
            aml_lines = wizard.line_ids.filtered(lambda line: line.flag == 'new_aml')
            self.assertEqual(len(aml_lines), 3)
            batch_lines = wizard.line_ids.filtered(lambda line: line.flag == 'new_batch')
            self.assertFalse(batch_lines)
            self.assertEqual(sorted(wizard.line_ids.mapped('balance')), [-100.0, -60.0, -30.0, 2.0, 188.0])
        wizard._action_validate()
        self.assertRecordValues(payments, [{'state': 'paid'}] * 3)
        self.assertRecordValues(invoices, [
            {'amount_residual':   0.0},
            {'amount_residual':  70.0},
            {'amount_residual': 140.0},
        ])

    def test_partner_account_batch_payments(self):
        """ Test that account receivable is used for inbound payments and account payable for outbound ones """
        for payment_type, account_a, account_b in [
            ('inbound', self.partner_a.property_account_receivable_id, self.partner_b.property_account_receivable_id),
            ('outbound', self.partner_a.property_account_payable_id, self.partner_b.property_account_payable_id),
        ]:
            payment_1 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.payment_method_line.id,
                'amount': 100.0,
            })
            payment_2 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer',
                'partner_id': self.partner_b.id,
                'payment_method_line_id': self.payment_method_line.id,
                'amount': 200.0,
            })
            payments = payment_1 + payment_2
            payments.action_post()
            batch = self.env['account.batch.payment'].create({
                'batch_type': payment_type,
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_ids': [Command.set(payments.ids)],
                'payment_method_id': self.payment_method_line.payment_method_id.id,
            })
            batch.validate_batch()
            st_line_amount = 300.0 if payment_type == 'inbound' else -300.0
            st_line = self._create_st_line(st_line_amount, payment_ref=batch.name)
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_add_new_batch_payments(batch)
            wizard._action_validate()
            bank_account = st_line.journal_id.default_account_id
            if self.module == 'accounting':
                if payment_type == 'inbound':
                    self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                        {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                        {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                        {'account_id': bank_account.id, 'partner_id': False, 'balance': 300.0},
                    ])
                else:
                    self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                        {'account_id': bank_account.id, 'partner_id': False, 'balance': -300.0},
                        {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                        {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                    ])
            else:
                outstanding = self.env['account.payment']._get_outstanding_account(payment_type)
                if payment_type == 'inbound':
                    self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                        {'account_id': outstanding.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                        {'account_id': outstanding.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                        {'account_id': bank_account.id, 'partner_id': False, 'balance': 300.0},
                    ])
                else:
                    self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                        {'account_id': bank_account.id, 'partner_id': False, 'balance': -300.0},
                        {'account_id': outstanding.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                        {'account_id': outstanding.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                    ])

    def test_batch_reconciliation_multiple_installments_payment_term(self):
        """ Test reconciliation of payments for multiple installments payment term lines """
        payment_term = self.env['account.payment.term'].create({
            'name': "20-80_payment_term",
            'company_id': self.company_data['company'].id,
            'line_ids': [
                Command.create({'value': 'percent', 'value_amount': 20, 'nb_days': 0}),
                Command.create({'value': 'percent', 'value_amount': 80, 'nb_days': 20}),
            ],
        })
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0])
        invoice.invoice_payment_term_id = payment_term
        invoice.action_post()
        # register payment for the first installment
        payment_1 = self._register_payment(invoice, amount=200.0)
        batch_1 = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment_1.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch_1.validate_batch()
        st_line_1 = self._create_st_line(200.0, payment_ref=batch_1.name, partner_id=self.partner_a.id)
        wizard_1 = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line_1.id).new({})
        wizard_1._action_add_new_batch_payments(batch_1)
        wizard_1._action_validate()

        bank_account = st_line_1.journal_id.default_account_id
        receivable_account = self.partner_a.property_account_receivable_id

        if self.module == 'accounting':
            self.assertRecordValues(st_line_1.move_id.line_ids.sorted('balance'), [
                {'account_id': receivable_account.id, 'balance': -200.0},
                {'account_id': bank_account.id, 'balance': 200.0},
            ])
        else:
            outstanding = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line_1.move_id.line_ids.sorted('balance'), [
                {'account_id': outstanding.id, 'balance': -200.0},
                {'account_id': bank_account.id, 'balance': 200.0},
            ])

        # register payment for the second installment
        payment_2 = self._register_payment(invoice, amount=800.0)
        batch_2 = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment_2.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch_2.validate_batch()
        st_line_2 = self._create_st_line(800.0, payment_ref=batch_2.name, partner_id=self.partner_a.id)
        wizard_2 = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line_2.id).new({})
        wizard_2._action_add_new_batch_payments(batch_2)
        wizard_2._action_validate()

        if self.module == 'accounting':
            self.assertRecordValues(st_line_2.move_id.line_ids.sorted('balance'), [
                {'account_id': receivable_account.id, 'balance': -800.0},
                {'account_id': bank_account.id, 'balance': 800.0},
            ])
        else:
            outstanding = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line_2.move_id.line_ids.sorted('balance'), [
                {'account_id': outstanding.id, 'balance': -800.0},
                {'account_id': bank_account.id, 'balance': 800.0},
            ])
        # both payment term lines of the invoice should be reconciled
        self.assertRecordValues(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('balance'), [
            {'balance': 200.0, 'amount_residual': 0.0, 'reconciled': True},
            {'balance': 800.0, 'amount_residual': 0.0, 'reconciled': True},
        ])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithoutEntryInvoicingOnly(CommonInvoicingOnly, TestBankRecWidgetWithoutEntry):
    allow_inherited_tests_method=True


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithEntry(CommonAccountingInstalled, TestBankRecWidgetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_method_line.payment_account_id = cls.inbound_payment_method_line.payment_account_id

    def test_matching_batch_payment(self):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 100.0,
        })
        payment.action_post()

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        self.assertRecordValues(batch, [{'state': 'draft'}])

        # Validate the batch and print it.
        batch.validate_batch()
        batch.print_batch_payment()
        self.assertRecordValues(batch, [{'state': 'sent'}])

        st_line = self._create_st_line(1000.0, payment_ref=f"turlututu {batch.name} tsointsoin", partner_id=self.partner_a.id)

        # Create a rule matching the batch payment.
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()
        rule = self._create_reconcile_model()

        # Ensure the rule matched the batch.
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_trigger_matching_rules()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0,  'reconcile_model_id': False},
            {'flag': 'new_aml',         'balance': -100.0,  'reconcile_model_id': rule.id},
            {'flag': 'auto_balance',    'balance': -900.0,  'reconcile_model_id': False},
        ])
        self.assertRecordValues(wizard, [{
            'state': 'valid',
        }])
        wizard._action_validate()

        self.assertRecordValues(batch, [{'state': 'reconciled'}])
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'account_id': st_line.journal_id.default_account_id.id,         'balance': 1000.0, 'reconciled': False},
            {'account_id': payment.outstanding_account_id.id,                'balance': -100.0, 'reconciled': True},
            {'account_id': self.partner_a.property_account_receivable_id.id, 'balance': -900.0, 'reconciled': False},
        ])

    def test_single_payment_from_batch_on_bank_reco_widget(self):
        payments = self.env['account.payment'].create([
            {
                'date': '2018-01-01',
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.payment_method_line.id,
                'amount': i * 100.0,
            }
            for i in range(1, 4)
        ])
        payments.action_post()

        # Add payments to a batch.
        batch_payment = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        st_line = self._create_st_line(100.0, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        # Add payment1 from the aml tab
        aml = payments[0].move_id.line_ids.filtered(lambda x: x.account_id.account_type != 'asset_receivable')
        wizard._action_add_new_amls(aml)

        # Validate with one payment inside a batch should reconcile directly the statement line.
        wizard._js_action_validate()
        self.assertTrue(wizard.return_todo_command)
        self.assertTrue(wizard.return_todo_command.get('done'))

        self.assertEqual(batch_payment.amount_residual, sum(payments[1:].mapped('amount')), "The batch amount should change following payment reconciliation")

    def test_multiple_exchange_diffs_in_batch(self):
        # Create a statement line when the currency rate is 1 USD == 2 EUR == 4 CAD
        st_line = self._create_st_line(
            1000.0,
            partner_id=self.partner_a.id,
            date='2017-01-01'
        )
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_line_ids=[{'price_unit': 5000.0, 'tax_ids': []}],
        )
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 100.0,
        })
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 200.0,
        })
        # Payment when 1 USD == 3 EUR
        payment_eur_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 240.0,
        })
        # Payment when 1 USD == 6 CAD
        payment_cad_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency_2.id,
            'amount': 300.0,
        })
        payments = payment_eur_gain_diff + payment_eur_gain_diff_2 + payment_eur_loss_diff + payment_cad_loss_diff
        payments.action_post()

        self.assertRecordValues(payments.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_current'), [
            {'balance': 100.0, 'amount_currency': 100.0, 'amount_residual': 100.0},
            {'balance': 200.0, 'amount_currency': 200.0, 'amount_residual': 200.0},
            {'balance':  80.0, 'amount_currency': 240.0, 'amount_residual':  80.0},
            {'balance':  50.0, 'amount_currency': 300.0, 'amount_residual':  50.0},
        ])

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'new_aml',         'balance': -1000.0},
        ])

        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_batch',       'amount_currency': -430.0,     'balance': -430.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 150.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -40.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -25.0},
        ])

        wizard._action_expand_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_aml',         'amount_currency': -100.0,     'balance': -100.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 50.0},
            {'flag': 'new_aml',         'amount_currency': -200.0,     'balance': -200.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 100.0},
            {'flag': 'new_aml',         'amount_currency': -240.0,     'balance': -80.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -40.0},
            {'flag': 'new_aml',         'amount_currency': -300.0,     'balance': -50.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -25.0},
        ])

        wizard._js_action_validate()
        A, B, C, D, E, F = st_line.move_id.line_ids.mapped('matching_number')
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'balance':   1000.0, 'amount_currency':   1000.0, 'amount_residual':   1000.0, 'matching_number': A},
            {'balance':   -655.0, 'amount_currency':   -655.0, 'amount_residual':      0.0, 'matching_number': B},
            {'balance':    -50.0, 'amount_currency':   -100.0, 'amount_residual':      0.0, 'matching_number': C},
            {'balance':   -100.0, 'amount_currency':   -200.0, 'amount_residual':      0.0, 'matching_number': D},
            {'balance':   -120.0, 'amount_currency':   -240.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':    -75.0, 'amount_currency':   -300.0, 'amount_residual':      0.0, 'matching_number': F},
        ])

        reconciled = st_line.move_id.line_ids.matched_debit_ids.debit_move_id | st_line.move_id.line_ids.matched_credit_ids.credit_move_id
        self.assertRecordValues(reconciled, [
            {'balance':   5000.0, 'amount_currency':   5000.0, 'amount_residual':   4345.0, 'matching_number': B},
            {'balance':    100.0, 'amount_currency':    100.0, 'amount_residual':      0.0, 'matching_number': C},
            {'balance':    200.0, 'amount_currency':    200.0, 'amount_residual':      0.0, 'matching_number': D},
            {'balance':     40.0, 'amount_currency':      0.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':     80.0, 'amount_currency':    240.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':     25.0, 'amount_currency':      0.0, 'amount_residual':      0.0, 'matching_number': F},
            {'balance':     50.0, 'amount_currency':    300.0, 'amount_residual':      0.0, 'matching_number': F},
        ])
        self.assertRecordValues(payments.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_current'), [
            {'balance':    100.0, 'amount_currency':    100.0, 'amount_residual':      0.0},
            {'balance':    200.0, 'amount_currency':    200.0, 'amount_residual':      0.0},
            {'balance':     80.0, 'amount_currency':    240.0, 'amount_residual':      0.0},
            {'balance':     50.0, 'amount_currency':    300.0, 'amount_residual':      0.0},
        ])

    def test_batch_payment_different_customers_epd_no_tax(self):
        """Total Discount loss should split and assigned to the correct partner
        Steps:
        - create two invoices with a different partner (epd + no tax on the lines)
        - register for each a payment (payment method with no outstanding account)
        - select the two payments and create a batch
        - create a transaction with an amount equal to two payments (discounted amount)
        - reconcile it with the batch payment
        """
        self.payment_method_line.payment_account_id = False
        invoices = (self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=False)
                    + self.init_invoice('out_invoice', partner=self.partner_b, amounts=[100.0], post=False)
                    )
        invoices.invoice_payment_term_id = self.early_payment_term
        invoices.action_post()

        payments = self._register_payment(invoices, payment_date=invoices[0].invoice_date)
        self.assertEqual(sum(payments.mapped('amount')), 196.0)

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(196.0, payment_ref=batch.name)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        if self.module == 'accounting':
            self.assertTrue(wizard._check_for_epd(batch))
            epd_line = wizard.line_ids.filtered(lambda line: line.flag == 'early_payment')
            self.assertTrue(epd_line)
            self.assertEqual(len(wizard.line_ids.mapped('partner_id')), 2, "There should be one EPD line per partner")
            self.assertEqual(sorted(wizard.line_ids.mapped('balance')), [-100.0, -100.0, 2.0, 2.0, 196.0])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithEntryInvoicingOnly(CommonInvoicingOnly, TestBankRecWidgetWithEntry):
    allow_inherited_tests_method=True
