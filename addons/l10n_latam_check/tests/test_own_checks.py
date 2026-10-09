# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.tests import Form, tagged
from odoo import Command, fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOwnChecks(L10nLatamCheckTest):

    def test_01_pay_with_own_checks(self):
        """ Create and post a manual checks with deferred date """

        with Form(self.env['account.payment'].with_context(default_payment_type='outbound')) as payment_form:
            payment_form.partner_id = self.partner_a
            payment_form.journal_id = self.bank_journal
            payment_form.payment_method_line_id = self.bank_journal._get_available_payment_method_lines(
                'outbound').filtered(lambda x: x.code == 'own_checks')[0]
            payment_form.memo = 'Deferred check'
            with payment_form.l10n_latam_new_check_ids.new() as check1:
                check1.name = '00000001'
                check1.payment_date = fields.Date.add(fields.Date.today(), months=1)
                check1.issuer_vat = '30714295698'
                check1.amount = 25

            with payment_form.l10n_latam_new_check_ids.new() as check2:
                check2.name = '00000002'
                check2.payment_date = fields.Date.add(fields.Date.today(), months=1)
                check2.issuer_vat = '30714295698'
                check2.amount = 25

        payment = payment_form.save()
        payment.action_post()
        self.assertEqual(payment.amount, 50)
        outstanding_line_ids = payment.l10n_latam_new_check_ids.mapped('outstanding_line_id')
        self.assertEqual(len(outstanding_line_ids), 2, "There should be a split line per check. (2)")
        all_handed = any(s == 'handed' for s in payment.l10n_latam_new_check_ids.mapped('issue_state'))
        self.assertTrue(all_handed, "All checks should be in handed status.")
        first_check = payment.l10n_latam_new_check_ids[0]
        first_check.action_void()
        self.assertTrue(first_check.issue_state == 'voided', "First checks should be in voided status.")

    def test_02_pay_with_own_check_and_cancel_payment(self):
        """ Create and post a manual check with deferred date ands cancel it """

        with Form(self.env['account.payment'].with_context(default_payment_type='outbound')) as payment_form:
            payment_form.partner_id = self.partner_a
            payment_form.journal_id = self.bank_journal
            payment_form.payment_method_line_id = self.bank_journal._get_available_payment_method_lines(
                'outbound').filtered(lambda x: x.code == 'own_checks')[0]

            payment_form.memo = 'Deferred check'
            with payment_form.l10n_latam_new_check_ids.new() as check1:
                check1.name = '00000003'
                check1.payment_date = fields.Date.add(fields.Date.today(), months=1)
                check1.issuer_vat = '30714295698'
                check1.amount = 50

        payment = payment_form.save()
        payment.action_post()
        self.assertEqual(payment.amount, 50)
        payment.action_cancel()
        self.assertFalse(payment.l10n_latam_new_check_ids.issue_state,
                         "Canceled payment checks must not have issue state")
        self.assertEqual(len(payment.l10n_latam_new_check_ids.outstanding_line_id), 0,
                         "Canceled payment checks must not have split move")

    def test_post_own_check_with_3_lines(self):
        foreign_currency = self.env.ref('base.EUR')
        foreign_currency.active = True
        payment_method_line = self.bank_journal._get_available_payment_method_lines('outbound').filtered_domain([('code', '=', 'own_checks')])[:1]
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
            'currency_id': foreign_currency.id,
            'payment_method_line_id': payment_method_line.id,
            'l10n_latam_new_check_ids': [
                Command.create({
                    'payment_date': fields.Date.today(),
                    'amount': '20',
                }),
                Command.create({
                    'payment_date': fields.Date.today(),
                    'amount': '30',
                }),
                Command.create({
                    'payment_date': fields.Date.today(),
                    'amount': '70',
                }),
            ]
        })
        payment.action_post()
        self.assertEqual(payment.amount, 120)

    def _create_own_checks_payment(self, amounts, first_number=100, **kwargs):
        payment_method_line = self.bank_journal._get_available_payment_method_lines('outbound').filtered_domain([('code', '=', 'own_checks')])[:1]
        return self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': payment_method_line.id,
            'l10n_latam_new_check_ids': [
                Command.create({
                    'name': '%08d' % (first_number + i),
                    'payment_date': fields.Date.add(fields.Date.today(), months=1),
                    'amount': amount,
                })
                for i, amount in enumerate(amounts)
            ],
            **kwargs,
        })

    def _debit_check(self, check):
        """ Simulate the bank debiting the check: clear its outstanding line against the bank account. """
        check_line = check.outstanding_line_id
        bank_move = self.env['account.move'].create({
            'journal_id': self.bank_journal.id,
            'line_ids': [
                Command.create({
                    'account_id': check_line.account_id.id,
                    'partner_id': check_line.partner_id.id,
                    'debit': check_line.credit,
                }),
                Command.create({
                    'account_id': self.bank_journal.default_account_id.id,
                    'credit': check_line.credit,
                }),
            ],
        })
        bank_move.action_post()
        (bank_move.line_ids.filtered(lambda l: l.account_id == check_line.account_id) + check_line).reconcile()
        self.assertEqual(check.issue_state, 'debited')

    def test_own_checks_split_payment_in_process_until_debited(self):
        """ A payment with several own checks must stay 'In Process' (not matched) until all the
        checks are debited, like a payment with a single check does. """
        payment = self._create_own_checks_payment([25, 25])
        payment.action_post()
        self.assertEqual(len(payment.l10n_latam_new_check_ids.outstanding_line_id.move_id - payment.move_id), 1, "A split move is expected")
        self.assertEqual(payment.state, 'in_process')
        self.assertFalse(payment.is_matched)

        first_check, second_check = payment.l10n_latam_new_check_ids
        self._debit_check(first_check)
        self.assertEqual(payment.state, 'in_process', "One check is still handed")
        self.assertFalse(payment.is_matched)

        self._debit_check(second_check)
        self.assertEqual(payment.state, 'paid')
        self.assertTrue(payment.is_matched)

    def test_own_check_single_vs_split_same_state(self):
        """ The number of checks must not change the payment state. """
        single = self._create_own_checks_payment([50])
        split = self._create_own_checks_payment([20, 30], first_number=200)
        (single + split).action_post()
        self.assertEqual(single.state, 'in_process')
        self.assertRecordValues(split, [{'state': single.state, 'is_matched': single.is_matched}])

    def test_own_checks_split_payment_bill_in_payment(self):
        """ Paying a bill with several own checks must leave the bill 'In Payment' (accounting installed). """
        self.ensure_installed('l10n_ar')
        bill = self._create_invoice(
            company_id=self.company_data_3['company'].id,
            partner_id=self.partner_a.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100, product_id=self.product_a)],
            move_type='in_invoice',
            l10n_latam_document_type_id=self.env.ref('l10n_ar.dc_liq_uci_a'),
            l10n_latam_document_number="001-00002",
            post=True
        )
        payment_method_line = self.bank_journal._get_available_payment_method_lines('outbound').filtered_domain([('code', '=', 'own_checks')])[:1]
        with patch.object(self.env.registry['account.move'], '_get_invoice_in_payment_state', return_value='in_payment'):
            action = bill.action_register_payment()
            wizard = self.env[action['res_model']].with_context(action['context']).create({
                'journal_id': self.bank_journal.id,
                'payment_method_line_id': payment_method_line.id,
                'l10n_latam_new_check_ids': [
                    Command.create({'name': '00000201', 'payment_date': fields.Date.today(), 'amount': bill.amount_total / 2}),
                    Command.create({'name': '00000202', 'payment_date': fields.Date.today(), 'amount': bill.amount_total / 2}),
                ],
            })
            payment = self.env['account.payment'].browse(wizard.action_create_payments()['res_id'])
            self.assertEqual(payment.state, 'in_process')
            self.assertEqual(bill.payment_state, 'in_payment')

            for check in payment.l10n_latam_new_check_ids:
                self._debit_check(check)
            self.assertEqual(payment.state, 'paid')
            self.assertEqual(bill.payment_state, 'paid')
