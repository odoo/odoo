# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form
from odoo.exceptions import UserError

from .test_hr_payroll_account import TestHrPayrollAccountCommon


@tagged('post_install', '-at_install')
class TestHrPayrollPayment(TestHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credit_account = cls.env['account.account'].create({
            'name': 'Salary Payble',
            'code': '2300',
            'reconcile': True,
            'account_type': 'liability_current',
        })
        cls.env['hr.salary.rule'].create({
            'name': 'Net Salary',
            'amount_select': 'code',
            'amount_python_compute': 'result = categories["BASIC"] + categories["ALW"] + categories["DED"]',
            'code': 'NET',
            'category_id': cls.env.ref('hr_payroll.NET').id,
            'sequence': 10,
            'account_credit': cls.credit_account.id,
            'struct_id': cls.hr_structure_softwaredeveloper.id,
        })

        cls.hr_employee_john.bank_account_id = cls.env['res.partner.bank'].create([{
            'acc_number': '0144748555',
            'partner_id': cls.hr_employee_john.work_contact_id.id,
            'allow_out_payment': True,
        }])

        cls.hr_payslip_john.action_refresh_from_work_entries()

    def test_payment_hr_payslip(self):
        """ Checking the process of a payslip when you register payment.  """

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

        with self.assertRaisesRegex(UserError, "You can only register payment for posted journal entries."):
            # Should not register payment for a non-posted journal entry
            self.hr_payslip_john.action_register_payment()

        # I register payment for the payslip.
        self.hr_payslip_john.move_id.action_post()
        self.assertEqual(self.hr_payslip_john.move_id.state, 'posted', 'Accounting entry has not been posted!')
        action_register_payment = self.hr_payslip_john.action_register_payment()
        action_register_payment["context"]["hr_payroll_payment_register"] = True

        # Use Form to ensure the computes and defaults are computed pre-create
        wizard = Form.from_action(self.env, action_register_payment)
        self.assertEqual(wizard.partner_id, self.hr_employee_john.work_contact_id, 'Partner is not correct!')
        self.assertEqual(wizard.amount, self.hr_payslip_john.move_id.amount_total, 'Amount is not correct!')
        self.assertEqual(wizard.partner_bank_id, self.hr_employee_john.bank_account_id, 'Bank account is not correct!')
        action_create_payment = wizard.save().action_create_payments()
        payment = self.env[action_create_payment['res_model']].browse(action_create_payment['res_id'])
        self.assertAlmostEqual(payment.amount, self.hr_payslip_john.move_id.amount_total, 'Payment amount is not correct!')
        self.assertEqual(payment.partner_bank_id, self.hr_employee_john.bank_account_id)

    def test_hr_payslip_payment_reverse(self):
        payslip = self.hr_payslip_john
        payslip.journal_id.write({'default_account_id': self.credit_account.id})
        asset_cash =  self.env['account.account'].create({
            'code': '1015101',
            'name': 'asset cash',
            'account_type': 'asset_cash',
        })
        salary_journal = self.env['account.journal'].create({
            'code': 'SLRS',
            'name': 'salary journal',
            'company_id': self.env.company.id,
            'type': 'general',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()

        self.assertEqual(payslip.state, 'done')
        self.assertTrue(payslip.move_id)

        payslip.move_id.line_ids.unlink()
        payslip.move_id.write({
            'move_type': 'entry',
            'journal_id': salary_journal.id,
            'payslip_ids': payslip.ids,
            'line_ids': [
                (0, 0, {
                    'debit': 1200.0,
                    'credit': 0.0,
                    'account_id': asset_cash.id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1200.0,
                    'account_id': self.credit_account.id,
                }),
            ],
        })

        payslip.move_id.action_post()
        action_register_payment = payslip.action_register_payment()

        wizard =  self.env['account.payment.register'].with_context(action_register_payment['context'],
            hr_payroll_payment_register=True,
            dont_redirect_to_payments=True,
        )
        account_payment = Form(wizard)
        account_payment.journal_id = self.env['account.journal'].search([
            ('name', 'ilike', 'bank'),
            ('company_id', '=', self.env.company.id)],
            limit=1
        )
        acc_payment = account_payment.save()
        acc_payment.action_create_payments()
        payment = self.env['account.payment'].search([('invoice_ids', '=', payslip.move_id.id)], limit=1)
        self.assertTrue(payment)
        self.assertEqual(payment.currency_id, self.env.company.currency_id)

        reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids= payslip.move_id.ids).create({
        'journal_id': salary_journal.id,
        }).refund_moves()

        reversal = self.env['account.move'].browse(reversal['res_id'])
        self.assertRecordValues(reversal.line_ids, [
            {
                'account_id':asset_cash.id,
                'debit': 0.0,
                'credit': 1200.0,
            },
            {
                'account_id': self.credit_account.id,
                'debit': 1200.0,
                'credit':0.0,
            }
        ])
