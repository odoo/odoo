# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged, Form

from .common import L10nPayrollAccountCommon


@tagged("post_install_l10n", "post_install", "-at_install", "aba_file")
class TestPayslipRun(L10nPayrollAccountCommon):

    def _prepare_payslip_run(self):
        payslip_run = self.env["hr.payslip.run"].create(
            {
                "date_start": "2023-01-01",
                "date_end": "2023-01-31",
                "name": "January Batch",
                "company_id": self.company.id,
            }
        )

        payslip_employee = (
            self.env["hr.payslip.employees"]
            .with_company(self.company)
            .create(
                {
                    "employee_ids": [
                        Command.set([self.employee_1.id, self.employee_2.id])
                    ]
                }
            )
        )
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.action_validate()
        return payslip_run

    @freeze_time("2023-01-31")
    def test_batch_payment(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(
            payslip_run.state, "close", "Payslip run should be in close state"
        )
        # Post journal entries
        payslip_run.slip_ids.move_id._post()
        payments = self._register_payment(payslip_run)

        self.assertEqual(payslip_run.l10n_au_payment_batch_id.payment_ids, payments)
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.batch_type, "outbound")
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.payment_method_id, self.env.ref("l10n_au_aba.account_payment_method_aba_ct"))

        self.assertTrue(all(payslip.state == 'paid' for payslip in payslip_run.slip_ids), "All payslips must be marked paid!")
        self.assertEqual(payslip_run.state, 'paid', "The payslip batch should be marked as paid!")
        for payment in payments:
            slip = payslip_run.slip_ids.filtered(lambda p: p.employee_id.work_contact_id == payment.partner_id)
            self.assertEqual(payment.amount, slip.line_ids.filtered(lambda x: x.code == 'NET').total)
            self.assertEqual(payment.partner_bank_id, slip.employee_id.bank_account_id, "The Payment should be made to bank account on the Employee!")

        payslip_run.l10n_au_payment_batch_id.validate_batch()
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.state, "sent", "Batch Should be in sent state!")
        self.assertTrue(payslip_run.l10n_au_payment_batch_id.export_file, "Aba File should be generated!")

        # Check Reconcialiation
        self.assertTrue(all(p.is_reconciled for p in payments), "All payments should be reconciled!")

        # Create Statement
        stmnt = self.env['account.bank.statement'].create({
            'name': 'Test Bank Statement',
            'date': '2014-12-31',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'line_ids': [
                Command.create({'payment_ref': 'Net Salary', 'amount': 4068.0, 'journal_id': self.bank_journal.id, 'partner_id': self.employee_1.work_contact_id.id}),
                Command.create({'payment_ref': 'Net Salary', 'amount': 5375.0, 'journal_id': self.bank_journal.id, 'partner_id': self.employee_2.work_contact_id.id}),
            ],
        })

        for st_line in stmnt.line_ids:
            payment_lines = payments.filtered(lambda x: x.partner_id == st_line.partner_id)\
                .move_id.line_ids.filtered(lambda line: line.account_id == self.aba_ct.payment_account_id)
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_add_new_amls(payment_lines, allow_partial=False)
            wizard._action_validate()
        self.assertTrue(all(p.is_matched for p in payments), "All payments should be Matched with bank statements!")

        self.assertEqual(payslip_run.l10n_au_payment_batch_id.state, "reconciled", "Batch Should be in reconciled state!")

    def test_payslip_aba(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(
            payslip_run.state, "close", "Payslip run should be in close state"
        )
        action = payslip_run.action_payment_report('aba')
        self.env["hr.payroll.payment.report.wizard"].with_context(
            **action["context"]
        ).create({}).generate_payment_report()
        self.assertTrue(payslip_run.payment_report, "Aba File should be generated!")

        payslip_run.slip_ids.move_id._post()
        self._register_payment(payslip_run)
        payslip_run.l10n_au_payment_batch_id.validate_batch()

        self.assertEqual(
            payslip_run.l10n_au_payment_batch_id.export_file,
            payslip_run.payment_report
        )

    def test_single_payslip_payment(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(
            payslip_run.state, "close", "Payslip run should be in close state"
        )
        payslip_run.slip_ids.move_id._post()
        payslip = payslip_run.slip_ids[0]
        action = payslip.action_register_payment()
        action["context"].update({
            'hr_payroll_payment_register': True
        })
        payment_register = Form.from_action(self.env, action)
        self.assertTrue(payment_register.amount)

        action_create_payment = payment_register.save().action_create_payments()
        payment = self.env["account.payment"].browse(action_create_payment['res_id'])
        amount = sum(payslip.move_id.line_ids.filtered_domain([("partner_id", "!=", False), ("price_total", ">", 0)]).mapped("price_total"))
        self.assertAlmostEqual(payment.amount, amount, msg='Payment amount is not correct!')
        self.assertEqual(payment.partner_bank_id, payslip.employee_id.bank_account_id)
        self.assertTrue(payment.is_reconciled, 'Payment should be Reconciled!')

        stmnt = self.env['account.bank.statement'].create({
            'name': 'Test Bank Statement',
            'date': '2014-12-31',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'line_ids': [
                Command.create({'payment_ref': 'Net Salary', 'amount': 4068.0, 'journal_id': self.bank_journal.id, 'partner_id': self.employee_1.work_contact_id.id}),
            ],
        })
        for st_line in stmnt.line_ids:
            payment_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id == self.outbound_manual.payment_account_id)
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_add_new_amls(payment_lines, allow_partial=False)
            wizard._action_validate()
        self.assertTrue(payment.is_matched, 'Payment should be match with a bank statement line!')
