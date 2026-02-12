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

    def test_single_check_invoice_status(self):
        """ Verify that a Bill paid with a Single Own Check remains 'in_payment' until the bank statement clears it. """
        invoice = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner_a.id,
            "company_id": self.bank_journal.company_id.id,
            "invoice_date": fields.Date.today(),
            "l10n_latam_document_number": "00001-00000002",
            "l10n_latam_document_type_id": 1,
            "invoice_line_ids": [
                Command.create({
                    "name": "Single Product Test",
                    "price_unit": 1000.0,
                    "quantity": 1,
                })
            ],
        })
        invoice.action_post()

        own_checks_method = self.bank_journal._get_available_payment_method_lines("outbound").filtered(lambda x: x.code == "own_checks")[:1]

        ctx_wizard = {
            "active_model": "account.move",
            "active_ids": invoice.ids,
        }

        with Form(self.env["account.payment.register"].with_context(ctx_wizard)) as wizard_form:
            wizard_form.journal_id = self.bank_journal
            wizard_form.payment_method_line_id = own_checks_method

            with wizard_form.l10n_latam_new_check_ids.new() as check:
                check.name = "CHK-SINGLE-001"
                check.amount = 1000.0
                check.payment_date = fields.Date.today()

        wizard = wizard_form.save()
        action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(action["res_id"])

        self.assertEqual(payment.l10n_latam_new_check_ids.issue_state, "handed")
        self.assertEqual(invoice.payment_state, "in_payment")

        st_line = self.env["account.bank.statement.line"].create({
            "payment_ref": f"Clear {payment.l10n_latam_new_check_ids.name}",
            "journal_id": self.bank_journal.id,
            "amount": -1000.0,
            "date": fields.Date.today(),
            "partner_id": self.partner_a.id,
        })

        check_obj = payment.l10n_latam_new_check_ids
        _st_liq, st_suspense, _st_other = st_line.with_context(
            skip_account_move_synchronization=True
        )._seek_for_lines()
        st_suspense.account_id = check_obj.outstanding_line_id.account_id
        (st_suspense + check_obj.outstanding_line_id).reconcile()

        invoice.invalidate_recordset(["payment_state"])
        self.assertEqual(invoice.payment_state, "paid")

    def test_multi_check_invoice_status(self):
        """Verify that a Bill paid with multiple Own Checks remains 'in_payment' until cleared by the bank,
        validating that the bill correctly tracks the unreconciled status of individual check lines."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "company_id": self.bank_journal.company_id.id,
                "invoice_date": fields.Date.today(),
                "l10n_latam_document_number": "00001-00000001",
                "l10n_latam_document_type_id": 1,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test Product",
                            "price_unit": 500.0,
                            "quantity": 1,
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        own_checks_method = self.bank_journal._get_available_payment_method_lines("outbound").filtered(lambda x: x.code == "own_checks")[:1]

        ctx_wizard = {
            "active_model": "account.move",
            "active_ids": invoice.ids,
        }

        with Form(self.env["account.payment.register"].with_context(ctx_wizard)) as wizard_form:
            wizard_form.journal_id = self.bank_journal
            wizard_form.payment_method_line_id = own_checks_method

            with wizard_form.l10n_latam_new_check_ids.new() as check:
                check.name = "Check001"
                check.amount = 250.0
                check.payment_date = fields.Date.today()

            with wizard_form.l10n_latam_new_check_ids.new() as check:
                check.name = "Check002"
                check.amount = 250.0
                check.payment_date = fields.Date.today()

        wizard = wizard_form.save()
        action = wizard.action_create_payments()

        payment = self.env["account.payment"].browse(action["res_id"])

        self.assertEqual(invoice.payment_state, "in_payment")

        check_1 = payment.l10n_latam_new_check_ids[0]
        st_line_1 = self.env["account.bank.statement.line"].create(
            {
                "payment_ref": f"Clear {check_1.name}",
                "journal_id": self.bank_journal.id,
                "amount": -check_1.amount,
                "date": check_1.payment_date,
                "partner_id": self.partner_a.id,
            }
        )
        _st_liq_1, st_suspense_1, _st_other_1 = st_line_1.with_context(skip_account_move_synchronization=True)._seek_for_lines()
        st_suspense_1.account_id = check_1.outstanding_line_id.account_id
        (st_suspense_1 + check_1.outstanding_line_id).reconcile()

        invoice.invalidate_recordset(["payment_state"])
        self.assertEqual(invoice.payment_state, "in_payment")

        check_2 = payment.l10n_latam_new_check_ids[1]
        st_line_2 = self.env["account.bank.statement.line"].create(
            {
                "payment_ref": f"Clear {check_2.name}",
                "journal_id": self.bank_journal.id,
                "amount": -check_2.amount,
                "date": check_2.payment_date,
                "partner_id": self.partner_a.id,
            }
        )
        _st_liq_2, st_suspense_2, _st_other_2 = st_line_2.with_context(skip_account_move_synchronization=True)._seek_for_lines()
        st_suspense_2.account_id = check_2.outstanding_line_id.account_id
        (st_suspense_2 + check_2.outstanding_line_id).reconcile()

        invoice.invalidate_recordset(["payment_state"])
        self.assertEqual(invoice.payment_state, "paid")
