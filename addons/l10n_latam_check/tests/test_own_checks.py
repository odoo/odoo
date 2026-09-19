# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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

    def test_own_check_multicurrency_liquidity_amounts(self):
        """ Own checks issued in a currency different from the company one. Each
        check liquidity line must keep the check nominal in amount_currency (the
        payment currency) and its conversion to company currency in balance. The
        issue only shows up when the rate is not 1:1, so we set a controlled one. """
        company = self.company_data_3['company']
        company_currency = company.currency_id
        foreign_currency = self.env.ref('base.EUR')
        foreign_currency.active = True
        self.assertNotEqual(company_currency, foreign_currency)
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'currency_id': foreign_currency.id,
            'company_id': company.id,
            'rate': 4.0,
        })
        payment_method_line = self.bank_journal._get_available_payment_method_lines('outbound').filtered_domain([('code', '=', 'own_checks')])[:1]
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
            'currency_id': foreign_currency.id,
            'date': fields.Date.today(),
            'payment_method_line_id': payment_method_line.id,
            'l10n_latam_new_check_ids': [
                Command.create({'payment_date': fields.Date.today(), 'amount': 20}),
                Command.create({'payment_date': fields.Date.today(), 'amount': 30}),
                Command.create({'payment_date': fields.Date.today(), 'amount': 70}),
            ]
        })
        payment.action_post()
        self.assertEqual(payment.amount, 120)

        for check in payment.l10n_latam_new_check_ids:
            line = check.outstanding_line_id
            self.assertEqual(
                abs(line.amount_currency), check.amount,
                "Check liquidity line must hold the nominal in the payment currency")
            expected_balance = foreign_currency._convert(
                check.amount, company_currency, company, payment.date)
            self.assertEqual(
                abs(line.balance), expected_balance,
                "Check liquidity line balance must be the nominal converted to company currency")
