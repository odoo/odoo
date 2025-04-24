# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.tests import Form, tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOwnChecks(L10nLatamCheckTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.own_check_payment_method = cls.env['account.payment.method'].create({
            'name': 'Test Own Check',
            'code': 'own_checks',
            'payment_type': 'inbound',
        })

    def test_01_pay_with_own_checks(self):
        """ Create and post a manual checks with deferred date """

        with Form(self.env['account.payment'].with_context(default_payment_type='outbound')) as payment_form:
            payment_form.partner_id = self.partner_a
            payment_form.journal_id = self.bank_journal
            payment_form.payment_method_id = self.own_checks_method
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
            payment_form.payment_method_id = self.own_checks_method

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

    def test_available_journals_for_own_checks(self):
        '''When own check payment methods are chosen only bank journals should be available in the payment form,
        and when other types of journals are chosen this payment method should not be available.'''

        payment1 = self.env['account.payment'].with_company(self.ar_company).create({
            'payment_method_id': self.own_check_payment_method.id,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.bank_journal.id,
            'l10n_latam_new_check_ids': [
                Command.create({'name': '00000001', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                Command.create({'name': '00000002', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
            ],
        })
        self.assertEqual(set(payment1.available_journal_ids.mapped('type')), {'bank'})

        payment2 = self.env['account.payment'].with_company(self.ar_company).create({
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': self.third_party_check_journal.id,
            'l10n_latam_new_check_ids': [
                Command.create({'name': '00000003', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                Command.create({'name': '00000004', 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
            ],
        })
        self.assertFalse('own_check' in payment2.available_payment_method_ids.mapped('code'))
