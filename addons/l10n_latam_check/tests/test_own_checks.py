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

    def test_invoice_status_after_voided_check(self):
        invoice = self._create_invoice(
            company_id=self.company_data_3['company'].id,
            partner_id=self.partner_a.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100, product_id=self.product_a)],
            move_type='in_invoice',
            l10n_latam_document_type_id=self.env.ref('l10n_ar.dc_liq_uci_a'),
            l10n_latam_document_number="001-00001",
            post=True
        )

        payment_method_line = self.bank_journal._get_available_payment_method_lines('outbound').filtered_domain([('code', '=', 'own_checks')])[:1]
        action = invoice.action_register_payment()
        wizard = self.env[action['res_model']].with_context(action['context']).create({
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': payment_method_line.id,
            'l10n_latam_new_check_ids': [
                Command.create({
                    'name': '0000001',
                    'payment_date': fields.Date.today(),
                    'amount': invoice.amount_total,
                })
            ],
        })
        action = wizard.action_create_payments()

        payment = self.env['account.payment'].browse(action['res_id'])
        check = payment.l10n_latam_new_check_ids
        self.assertEqual(check.issue_state, 'handed', 'Own check should be in handed state after payment')

        # invoice status is not_paid -> original payment unreconciled, but still appears as outstanding debit on invoice
        # payment_line is reconciled -> payment now linked with void move and doesn't appear as outstanding debit
        check.action_void()
        self.assertEqual(check.issue_state, 'voided', 'Own check should be voided after action_void()')
        self.assertEqual(invoice.payment_state, 'not_paid', 'Invoice should return to not_paid after the check is voided')

        payment_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        self.assertTrue(payment_line.reconciled, "Original payment line should be reconciled with the void move")
