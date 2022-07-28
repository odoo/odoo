# -*- coding: utf-8 -*-
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

import freezegun


@tagged('post_install', '-at_install')
class TestAccountMoveDateAlgorithm(AccountTestInvoicingCommon):

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
                    **line_kwargs,
                })
                for line_kwargs in kwargs.get('invoice_line_ids', [{}])
            ],
        })

    def _create_payment(self, date, **kwargs):
        return self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            **kwargs,
            'date': date,
        })

    def _set_lock_date(self, lock_date):
        self.env.company.fiscalyear_lock_date = fields.Date.from_string(lock_date)

    def _reverse_invoice(self, invoice):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=invoice.ids)\
            .create({
                'journal_id': invoice.journal_id.id,
                'reason': "no reason",
                'refund_method': 'cancel',
            })
        reversal = move_reversal.reverse_moves()
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
        invoice = self._create_invoice('out_invoice', '2016-01-01', currency_id=self.currency_data['currency'].id)
        refund = self._create_invoice('out_refund', '2017-01-01', currency_id=self.currency_data['currency'].id)
        (invoice + refund).action_post()
        self._set_lock_date('2017-01-31')

        res = (invoice + refund).line_ids\
            .filtered(lambda x: x.account_id.internal_type == 'receivable')\
            .reconcile()
        exchange_move = res['full_reconcile'].exchange_move_id

        self.assertRecordValues(exchange_move, [{
            'date': fields.Date.from_string('2017-02-01'),
            'amount_total_signed': 200.0,
        }])

    @freezegun.freeze_time('2017-02-12')
    def test_unreconcile_with_lock_date(self):
        invoice = self._create_invoice('out_invoice', '2016-01-01', currency_id=self.currency_data['currency'].id)
        refund = self._create_invoice('out_refund', '2017-01-01', currency_id=self.currency_data['currency'].id)
        (invoice + refund).action_post()

        res = (invoice + refund).line_ids\
            .filtered(lambda x: x.account_id.internal_type == 'receivable')\
            .reconcile()
        exchange_move = res['full_reconcile'].exchange_move_id

        self._set_lock_date('2017-01-31')
        (invoice + refund).line_ids.remove_move_reconcile()

        reverse_exchange_move = exchange_move.line_ids.matched_credit_ids.credit_move_id.move_id
        self.assertRecordValues(reverse_exchange_move, [{
            'date': fields.Date.from_string('2017-02-12'),
            'amount_total_signed': 200.0,
        }])

    def test_caba_with_lock_date(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
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
            currency_id=self.currency_data['currency'].id,
            invoice_line_ids=[{'tax_ids': [Command.set(tax.ids)]}],
        )
        payment = self._create_payment('2016-02-01', amount=invoice.amount_total)
        (invoice + payment.move_id).action_post()

        self._set_lock_date('2017-01-03')

        with freezegun.freeze_time('2017-01-12'):
            (invoice + payment.move_id).line_ids\
                .filtered(lambda x: x.account_id.internal_type == 'receivable')\
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
