# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from lxml import etree
from datetime import date, datetime, timedelta

from odoo import Command, fields
from odoo.addons.hr_payroll_account.tests.test_hr_payroll_account import TestHrPayrollAccountCommon
from odoo.tests.common import test_xsd
from odoo.tests import tagged, Form


class TestPayrollSEPACreditTransferCommon(TestHrPayrollAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref('base.USD')
        cls.env.user.company_id.write({
            'iso20022_orgid_id': "0468651441",
            'country_id': cls.env.ref('base.us').id,
        })

        cls.bank = cls.env['res.bank'].create({
            'name': 'BNP',
            'bic': 'GEBABEBB',
        })

        cls.res_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'partner_id': cls.work_contact.id,
            'acc_type': 'bank',
            'bank_id': cls.bank.id,
        })

        cls.bank_partner = cls.env['res.partner.bank'].create({
            'acc_number': 'BE84567968814145',
            'acc_type': 'iban',
            'partner_id': cls.env.ref('base.main_company').partner_id.id,
        })

        cls.hr_employee_john.bank_account_id = cls.res_partner_bank

        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNK',
            'type': 'bank',
            'bank_id': cls.bank.id,
            'bank_account_id': cls.bank_partner.id,
        })
        cls.bank_journal.sepa_pain_version = 'pain.001.001.09'

        # ============================= MIURA =============================
        cls.miura_be_company = cls.env['res.company'].create({
            'name': 'Miura BE company',
            'country_id': cls.env.ref('base.be').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'batch_payroll_move_lines': False,
        })
        miura_transfer_account = cls.env['account.account'].create({
            'name': 'Miura Company Transfer Account',
            'code': '994987',
            'reconcile': True,
            'account_type': 'liability_payable',
            'company_ids': (cls.miura_be_company.id,),
        })
        cls.miura_be_company.transfer_account_id = miura_transfer_account.id
        cls.bnp_bank = cls.env['res.bank'].create({
            'name': 'Miura BNP',
            'bic': 'GEBABEBB',
        })
        cls.miura_work_contact = cls.env['res.partner'].create({'name': 'Miura work contact'})
        cls.miura_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE91073397502076',
            'partner_id': cls.miura_work_contact.id,
            'acc_type': 'bank',
            'bank_id': cls.bnp_bank.id,
            'allow_out_payment': True,
        })

        cls.salary_work_contact = cls.env['res.partner'].create({'name': 'Salary work contact'})
        cls.salary_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE34438537755990',
            'partner_id': cls.salary_work_contact.id,
            'acc_type': 'bank',
            'bank_id': cls.bnp_bank.id,
            'allow_out_payment': True,
        })

        cls.miura_work_address = cls.env['res.partner'].create({'name': 'Miura work address'})
        cls.hr_employee_miura = cls.env['hr.employee'].create({
           'work_contact_id': cls.miura_work_contact.id,
            'address_id': cls.miura_work_address.id,
            'birthday': '1966-07-11',
            'children': 0.0,
            'gender': 'male',
            'marital': 'single',
            'name': 'Kentaro',
            'bank_account_id': cls.miura_partner_bank.id,
            'company_id': cls.miura_be_company.id,
        })

        salary_payable = cls.env['account.account'].create({
            'name': 'Salary Payable',
            'code': '2300',
            'reconcile': True,
            'account_type': 'liability_payable',
            'company_ids': (cls.miura_be_company.id,),
        })

        salary_account = cls.env['account.account'].create({
            'name': "Salary Expense",
            'code': "092039",
            'account_type': "expense",
            'company_ids': (cls.miura_be_company.id,),
        })

        cls.miura_salaries_journal = cls.env['account.journal'].create({
            'name': 'Sepa Test Salaries',
            'type': 'credit',
            'code': 'SEPA-SLR-TEST',
            'default_account_id': salary_account.id,
            'sepa_pain_version': 'pain.001.001.09',
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.miura_be_company.id,
            'bank_account_id': cls.salary_partner_bank.id,
        })

        cls.hr_structure_mangaka = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Mangaka',
            'rule_ids': [
                (0, 0, {
                    'name': 'Basic Salary',
                    'amount_select': 'percentage',
                    'amount_percentage': 100,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'BASIC',
                    'category_id': cls.env.ref('hr_payroll.BASIC').id,
                    'sequence': 1,
                }), (0, 0, {
                    'name': 'Provident Fund',
                    'amount_select': 'percentage',
                    'sequence': 120,
                    'amount_percentage': -12.5,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'PF',
                    'category_id': cls.env.ref('hr_payroll.DED').id,
                }), (0, 0, {
                    'name': 'Meal Voucher',
                    'amount_select': 'fix',
                    'amount_fix': 10,
                   'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
                    'code': 'MA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 16,
                }), (0, 0, {
                    'name': 'Conveyance Allowance',
                    'amount_select': 'fix',
                    'amount_fix': 800,
                    'code': 'CA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 10,
                }), (0, 0, {
                    'name': 'House Rent Allowance',
                    'amount_select': 'percentage',
                    'amount_percentage': 40,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'HRA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 5,
                }), (0, 0, {
                    'name': 'Net Salary',
                    'amount_select': 'code',
                    'amount_python_compute': 'result = categories["BASIC"] + categories["ALW"] + categories["DED"]',
                    'code': 'NET',
                    'category_id': cls.env.ref('hr_payroll.NET').id,
                    'sequence': 200,
                    'account_credit': salary_payable.id,
                })

            ],
            'type_id': cls.env['hr.payroll.structure.type'].create({'name': 'Employee', 'country_id': False}).id,
            'journal_id': cls.miura_salaries_journal.id,
        })

        hr_structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Salary Structure Type',
            'struct_ids': [(4, cls.hr_structure_mangaka.id)],
            'default_struct_id': cls.hr_structure_mangaka.id,
        })

        cls.hr_contract_miura = cls.env['hr.contract'].create({
            'name': 'Miura contract',
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': date(2010, 1, 1),
            'wage': 5000.0,
            'employee_id': cls.hr_employee_miura.id,
            'structure_type_id': hr_structure_type.id,
        })

        cls.hr_payslip_miura = cls.env['hr.payslip'].create({
            'employee_id': cls.hr_employee_miura.id,
            'struct_id': cls.hr_structure_mangaka.id,
            'contract_id': cls.hr_contract_miura.id,
            'journal_id': cls.miura_salaries_journal.id,
            'name': 'Test Payslip Miura',
        })

        sepa_payment_method_line = cls.env['account.payment.method.line'].create({
            'payment_method_id': cls.env.ref('account_iso20022.account_payment_method_sepa_ct').id,
            'journal_id': cls.miura_salaries_journal.id,
        })

        cls.miura_salaries_journal.outbound_payment_method_line_ids |= sepa_payment_method_line


@tagged('post_install', '-at_install')
class TestPayrollSEPACreditTransfer(TestPayrollSEPACreditTransferCommon):
    def test_00_hr_payroll_account_iso20022(self):
        """ Checking the process of payslip when you create a SEPA payment. """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I make the SEPA payment.
        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.hr_payslip_john.ids,
            'payslip_run_id': self.hr_payslip_john.payslip_run_id.id,
            'export_format': 'sepa',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()

        # I verify if a file is created.
        self.assertTrue(file, 'SEPA payment has not been created!')

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State should not change!')

    def test_01_hr_payroll_account_iso20022(self):
        """ Checking the process of payslip run when you create a SEPA payment. """

        # I verify the payslip run is in draft state.
        self.assertEqual(self.payslip_run.state, 'draft', 'State not changed!')

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm the payslip run.
        self.payslip_run.action_validate()

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I make the SEPA payment.
        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.payslip_run.slip_ids.ids,
            'payslip_run_id': self.payslip_run.id,
            'export_format': 'sepa',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()

        # I verify if a file is created for the payslip run.
        self.assertTrue(file, 'SEPA payment has not been created!')

        # I verify the payslip is in paid state.
        self.assertEqual(self.payslip_run.state, 'close', 'State should not change!')

    def test_02_hr_payroll_account_iso20022_ch(self):
        self.assertEqual(self.payslip_run.state, 'draft')

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id)]
        })
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        self.assertTrue(len(self.payslip_run.slip_ids) > 0)
        self.assertEqual(self.payslip_run.state, 'verify')

        self.payslip_run.action_validate()

        self.assertEqual(self.payslip_run.state, 'close')

        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.payslip_run.slip_ids.ids,
            'payslip_run_id': self.payslip_run.id,
            'export_format': 'iso20022_ch',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()

        self.assertTrue(file)
        self.assertEqual(self.payslip_run.state, 'close')

    def test_sepa_payslip_partner_bank_id(self):
        """ Check that the "partner_bank_id" is set after account_register_payment wizard has
            been initialized and that the action_create_payments (action launched when the
            user clicks on "Create Payments" button of the account_register_payment wizard)
            doesn't raise any error.

            This test is not following any real spec, its only purpose is to check that the payslip
            sepa payment flow works (so feel free to modify it if you feel like something's wrong)
        """
        self.hr_payslip_miura.compute_sheet()
        self.hr_payslip_miura.action_payslip_done()
        self.hr_payslip_miura.move_id.action_post()

        sepa_payment_method_line = self.env['account.payment.method.line'].create({
            'payment_method_id': self.env.ref('account_iso20022.account_payment_method_sepa_ct').id,
            'journal_id': self.miura_salaries_journal.id,
        })

        action_register_payment = self.hr_payslip_miura.action_register_payment()
        register_payment_form = Form.from_action(self.env, action_register_payment)
        register_payment_form.payment_method_line_id = sepa_payment_method_line
        saved_form = register_payment_form.save()
        self.assertEqual(saved_form.partner_bank_id.id, self.miura_partner_bank.id)
        saved_form.action_create_payments()


@tagged('external_l10n', 'post_install', '-at_install', '-standard')
class TestPayrollSEPACreditTransferXmlValidity(TestPayrollSEPACreditTransferCommon):

    @test_xsd(path='account_sepa/schemas/pain.001.001.03.xsd')
    def test_00_hr_payroll_account_iso20022(self):
        """ Checking the process of payslip when you create a SEPA payment. """

        self.hr_payslip_john.action_payslip_done()
        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.hr_payslip_john.ids,
            'payslip_run_id': self.hr_payslip_john.payslip_run_id.id,
            'export_format': 'sepa',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()
        return etree.fromstring(base64.b64decode(file))

    @test_xsd(path='account_sepa/schemas/pain.001.001.03.xsd')
    def test_01_hr_payroll_account_iso20022(self):
        """ Checking the process of payslip run when you create a SEPA payment. """

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [Command.set(self.hr_employee_john.id)]
        })
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()
        self.payslip_run.action_validate()
        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.payslip_run.slip_ids.ids,
            'payslip_run_id': self.payslip_run.id,
            'export_format': 'sepa',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()

        return etree.fromstring(base64.b64decode(file))
