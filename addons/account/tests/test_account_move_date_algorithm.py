# -*- coding: utf-8 -*-
from contextlib import closing

import freezegun

from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveDateAlgorithm(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_invoice(self, move_type, date, **kwargs):
        return self.env['account.move'].create({
            'invoice_date': date,
            'partner_id': self.partner_a.id,
            **kwargs,
            'move_type': move_type,
            'date': date,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1200.0,
                    'tax_ids': [],
                    **line_kwargs,
                })
                for line_kwargs in kwargs.get('invoice_line_ids', [{}])
            ],
        })

    def _create_payment(self, date, **kwargs):
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            **kwargs,
            'date': date,
        })
        payment.action_post()
        return payment

    def _set_lock_date(self, lock_date):
        self.env.company.fiscalyear_lock_date = fields.Date.from_string(lock_date)

    def _reverse_invoice(self, invoice):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=invoice.ids)\
            .create({
                'journal_id': invoice.journal_id.id,
                'reason': "no reason",
            })
        reversal = move_reversal.refund_moves()
        return self.env['account.move'].browse(reversal['res_id'])

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    @freezegun.freeze_time('2017-01-12')
    def test_out_invoice_date_with_lock_date(self):
        self._set_lock_date('2016-12-31')
        move = self._create_invoice('out_invoice', '2016-01-01')
        move.action_post()

        self.assertRecordValues(move, [{
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_out_invoice_reverse_date_with_lock_date(self):
        move = self._create_invoice('out_invoice', '2016-01-01')
        move.action_post()
        self._set_lock_date('2016-12-31')
        reverse_move = self._reverse_invoice(move)

        self.assertRecordValues(reverse_move, [{
            'invoice_date': fields.Date.from_string('2017-01-12'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_out_refund_date_with_lock_date(self):
        self._set_lock_date('2016-12-31')
        move = self._create_invoice('out_refund', '2016-01-01')
        move.action_post()

        self.assertRecordValues(move, [{
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_out_refund_reverse_date_with_lock_date(self):
        move = self._create_invoice('out_refund', '2016-01-01')
        move.action_post()
        self._set_lock_date('2016-12-31')
        reverse_move = self._reverse_invoice(move)

        self.assertRecordValues(reverse_move, [{'date': fields.Date.from_string('2017-01-12')}])

    @freezegun.freeze_time('2017-01-12')
    def test_in_invoice_date_with_lock_date(self):
        self._set_lock_date('2016-12-31')
        move = self._create_invoice('in_invoice', '2016-01-01')
        move.action_post()

        self.assertRecordValues(move, [{
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_in_invoice_reverse_date_with_lock_date(self):
        move = self._create_invoice('in_invoice', '2016-01-01')
        move.action_post()
        self._set_lock_date('2016-12-31')
        reverse_move = self._reverse_invoice(move)

        self.assertRecordValues(reverse_move, [{
            'invoice_date': fields.Date.from_string('2017-01-12'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_in_refund_date_with_lock_date(self):
        self._set_lock_date('2016-12-31')
        move = self._create_invoice('in_refund', '2016-01-01')
        move.action_post()

        self.assertRecordValues(move, [{
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'date': fields.Date.from_string('2017-01-12'),
        }])

    @freezegun.freeze_time('2017-01-12')
    def test_in_refund_reverse_date_with_lock_date(self):
        move = self._create_invoice('in_refund', '2016-01-01')
        move.action_post()
        self._set_lock_date('2016-12-31')
        reverse_move = self._reverse_invoice(move)

        self.assertRecordValues(reverse_move, [{'date': fields.Date.from_string('2017-01-12')}])

    @freezegun.freeze_time('2017-02-12')
    def test_reconcile_with_lock_date(self):
        invoice = self._create_invoice('out_invoice', '2016-01-01', currency_id=self.other_currency.id)
        refund = self._create_invoice('out_refund', '2017-01-01', currency_id=self.other_currency.id)
        (invoice + refund).action_post()
        self._set_lock_date('2017-01-31')

        amls = (invoice + refund).line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        amls.reconcile()
        exchange_move = amls.matched_debit_ids.exchange_move_id

        self.assertRecordValues(exchange_move, [{
            'date': fields.Date.from_string('2017-02-12'),
            'amount_total_signed': 200.0,
        }])

    @freezegun.freeze_time('2017-02-12')
    def test_unreconcile_with_lock_date(self):
        invoice = self._create_invoice('out_invoice', '2016-01-01', currency_id=self.other_currency.id)
        refund = self._create_invoice('out_refund', '2017-01-01', currency_id=self.other_currency.id)
        (invoice + refund).action_post()

        amls = (invoice + refund).line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        amls.reconcile()
        exchange_move = amls.matched_debit_ids.exchange_move_id

        self._set_lock_date('2017-01-31')
        (invoice + refund).line_ids.remove_move_reconcile()

        reverse_exchange_move = exchange_move.line_ids.matched_credit_ids.credit_move_id.move_id
        self.assertRecordValues(reverse_exchange_move, [{
            'date': fields.Date.from_string('2017-02-12'),
            'amount_total_signed': 200.0,
        }])

    def test_caba_with_lock_date(self):
        self.env.company.tax_exigibility = True

        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        tax = self.env['account.tax'].create({
            'name': 'cash basis 10%',
            'type_tax_use': 'sale',
            'amount': 10,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': tax_waiting_account.id,
        })

        invoice = self._create_invoice(
            'out_invoice', '2016-01-01',
            currency_id=self.other_currency.id,
            invoice_line_ids=[{'tax_ids': [Command.set(tax.ids)]}],
        )
        payment = self._create_payment('2016-02-01', amount=invoice.amount_total)
        invoice.action_post()

        self._set_lock_date('2017-01-03')

        with freezegun.freeze_time('2017-01-12'):
            (invoice + payment.move_id).line_ids\
                .filtered(lambda x: x.account_id.account_type == 'asset_receivable')\
                .reconcile()

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])

        self.assertRecordValues(caba_move, [{
            'date': fields.Date.from_string('2017-01-12'),
            'amount_total_signed': 440.0,
        }])

        self._set_lock_date('2017-02-01')

        with freezegun.freeze_time('2017-03-12'):
            (invoice + payment.move_id).line_ids.remove_move_reconcile()

        reverse_exchange_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)]) - caba_move

        self.assertRecordValues(reverse_exchange_move, [{
            'date': fields.Date.from_string('2017-02-28'),
            'amount_total_signed': 440.0,
        }])

    @freezegun.freeze_time('2023-05-01')
    def test_caba_with_different_lock_dates(self):
        """
        Test the date of the CABA move when reconciling a payment in case the lock dates
        are different between post and reconciliation time (caba move creation time).
        Ensure that user groups (accountant rights) do not matter.
        """
        self.env.company.tax_exigibility = True

        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        tax = self.env['account.tax'].create({
            'name': 'cash basis 10%',
            'type_tax_use': 'sale',
            'amount': 10,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': tax_waiting_account.id,
        })

        # User groups do not matter
        for group in (
                'account.group_account_manager',
                'account.group_account_invoice',
        ):
            with self.subTest(group=group), closing(self.cr.savepoint()):
                self.env.user.groups_id = [Command.set(self.env.ref(group).ids)]

                self.assertTrue(self.env.user.has_group(group))

                invoice = self._create_invoice(
                    'out_invoice', '2023-01-02',
                    invoice_line_ids=[{'tax_ids': [Command.set(tax.ids)]}],
                )
                payment = self._create_payment('2023-01-30', amount=invoice.amount_total)

                self.env.company.sudo().sale_lock_date = fields.Date.to_date('2023-02-01')
                invoice.action_post()
                self.assertEqual(invoice.date.isoformat(), '2023-02-28')
                self.assertEqual(payment.move_id.date.isoformat(), '2023-01-30')

                self.env.company.sudo().sale_lock_date = fields.Date.to_date('2023-03-01')
                (invoice + payment.move_id).line_ids\
                    .filtered(lambda x: x.account_id.account_type == 'asset_receivable')\
                    .reconcile()

                caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])

                # The sale lock date does not matter for the caba move, since it is not in a sale journal
                self.assertEqual(caba_move.journal_id.type, 'general')
                self.assertEqual(caba_move.date.isoformat(), '2023-02-28')

    @freezegun.freeze_time('2024-08-05')
    def test_lock_date_exceptions(self):
        for lock_date_field, move_type in [
            ('fiscalyear_lock_date', 'out_invoice'),
            ('tax_lock_date', 'out_invoice'),
            ('sale_lock_date', 'out_invoice'),
            ('purchase_lock_date', 'in_invoice'),
        ]:
            with self.subTest(lock_date_field=lock_date_field, move_type=move_type):
                self.env.company[lock_date_field] = '2024-07-31'
                self.env['account.lock_exception'].create({
                    lock_date_field: fields.Date.to_date('2024-01-01'),
                    'end_datetime': False,
                })
                move = self.init_invoice(
                    move_type, amounts=[100], taxes=self.env.company.account_sale_tax_id,
                    invoice_date='2024-07-01', post=True
                )
                self.assertEqual(move.date, fields.Date.to_date('2024-07-01'))
