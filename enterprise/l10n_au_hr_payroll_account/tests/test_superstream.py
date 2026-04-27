# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from itertools import zip_longest
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged, new_test_user


@tagged("post_install_l10n", "post_install", "-at_install", "superstream")
class TestPayrollSuperStream(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(freeze_time(date(2023, 9, 1)))
        cls.account_21400 = cls.env['account.account'].search([
            ('company_ids', '=', cls.company_data['company'].id),
            ('code', '=', 21400)
        ])
        cls.australian_company = cls.company_data['company']
        cls.australian_company.write({
            "name": "My Superstream Australian Company",
            "country_id": cls.env.ref("base.au").id,
            "currency_id": cls.env.ref("base.AUD").id,
            "resource_calendar_id": cls.env.ref("l10n_au_hr_payroll.resource_calendar_au_38").id,
            "vat": '83 914 571 673',
        })
        clearing_house = cls.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house')
        clearing_house.with_company(cls.australian_company).property_account_payable_id = cls.account_21400
        bank_account = cls.env['res.partner.bank'].create({
            "acc_number": '12344321',
            "acc_type": 'aba',
            "aba_bsb": '123-456',
            "company_id": cls.australian_company.id,
            "partner_id": cls.australian_company.partner_id.id,
        })
        cls.journal_id = cls.env["account.journal"].create({
            "name": "Payslip Bank",
            "type": "bank",
            "aba_fic": "CBA",
            "aba_user_spec": "Test Ltd",
            "aba_user_number": "111111",
            "company_id": cls.australian_company.id,
            "bank_account_id": bank_account.id,
        })
        pay_method_line = cls.journal_id._get_available_payment_method_lines('outbound').filtered(
            lambda x: x.code == 'manual')
        pay_method_line.payment_account_id = cls.inbound_payment_method_line.payment_account_id
        cls.employee = cls.env['hr.employee'].create({
            'company_id': cls.australian_company.id,
            'resource_calendar_id': cls.australian_company.resource_calendar_id.id,
            'name': 'Roger Federer',
            'work_phone': '123456789',
            'private_street': 'Australian Street',
            'private_city': 'Sydney',
            "private_state_id": cls.env.ref("base.state_au_2").id,
            "private_zip": "2000",
            "private_country_id": cls.env.ref("base.au").id,
            'private_phone': '123456789',
            'private_email': 'roger@gmail.com',
            'birthday':  date(1970, 3, 21),
            'l10n_au_tfn_declaration': 'provided',
            'l10n_au_tfn': '999999661',
            'l10n_au_training_loan': True,
            'l10n_au_nat_3093_amount': 150,
            'l10n_au_child_support_garnishee_amount': 0.1,
            'l10n_au_child_support_deduction': 150,
            'l10n_au_payroll_id': 'odoo_f47ac10b_001',
            'gender': 'male',
        })
        cls.env['hr.contract'].create({
            'company_id': cls.australian_company.id,
            'resource_calendar_id': cls.australian_company.resource_calendar_id.id,
            'employee_id': cls.employee.id,
            'name': 'Roger Contract',
            'date_start': date(1975, 1, 1),
            'wage': 5000,
            'l10n_au_yearly_wage': 60000,
            'structure_type_id': cls.env.ref('l10n_au_hr_payroll.structure_type_schedule_1').id,
            'l10n_au_leave_loading': 'regular',
            'l10n_au_leave_loading_rate': 5,
            'l10n_au_workplace_giving': 100,
            'l10n_au_salary_sacrifice_superannuation': 20,
            'l10n_au_salary_sacrifice_other': 20,
            'state': 'open',
        })

        cls.super_fund = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund A',
            'abn': '2345678912',
            'address_id': cls.env['res.partner'].create({'name': "Fund A Partner"}).id,
        })
        smsf_partner = cls.env['res.partner'].create({'name': "Fund B"})
        cls.super_fund_smsf = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund B',
            'abn': '2345678913',
            'fund_type': 'SMSF',
            'bank_account_id': cls.env['res.partner.bank'].create({
                "acc_number": '12344322',
                "acc_type": 'aba',
                "aba_bsb": '123-457',
                "company_id": cls.australian_company.id,
                "partner_id": smsf_partner.id,
            }).id,
            'address_id': smsf_partner.id,
        })
        cls.super_account_a = cls.env['l10n_au.super.account'].create({
            "date_from": date(2023, 6, 1),
            "employee_id": cls.employee.id,
            "fund_id": cls.super_fund.id
        })
        cls.payslips = cls.env['hr.payslip'].create([{
            'company_id': cls.australian_company.id,
            'employee_id': cls.employee.id,
            'name': 'Roger Payslip August',
            'date_from': date(2023, 8, 1),
            'date_to': date(2023, 8, 31),
            'input_line_ids': [(5, 0, 0), (0, 0, {'input_type_id': cls.env.ref('hr_payroll.input_child_support').id, 'amount': 200})],
        },
        {
            'company_id': cls.australian_company.id,
            'employee_id': cls.employee.id,
            'name': 'Roger Payslip September',
            'date_from': date(2023, 9, 1),
            'date_to': date(2023, 9, 30),
            'input_line_ids': [(5, 0, 0), (0, 0, {'input_type_id': cls.env.ref('hr_payroll.input_child_support').id, 'amount': 200})],
        }])
        cls.employee_user = new_test_user(cls.env, login='mel', groups='hr.group_hr_manager')
        cls.australian_company.l10n_au_hr_super_responsible_id = cls.env["hr.employee"].create({
            "name": "Mel Gibson",
            "resource_calendar_id": cls.australian_company.resource_calendar_id.id,
            "company_id": cls.australian_company.id,
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_country_id": cls.env.ref("base.au").id,
            "work_phone": "123456789",
            "work_email": "mel@test.com",
            "birthday": date.today() - relativedelta(years=22),
            # fields modified in the tests
            "marital": "single",
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            "l10n_au_tax_free_threshold": True,
            "is_non_resident": False,
            "l10n_au_training_loan": False,
            "l10n_au_nat_3093_amount": 0,
            "l10n_au_child_support_garnishee_amount": 0,
            "l10n_au_medicare_exemption": "X",
            "l10n_au_medicare_surcharge": "X",
            "l10n_au_medicare_reduction": "X",
            "l10n_au_child_support_deduction": 0,
            # "l10n_au_previous_payroll_id": "odoo_f47ac10b_001",
            "user_id": cls.employee_user.id,
        })

    def _test_super_stream(self, superstream, expected_saff_lines: list, payment_total: float):
        superstream.journal_id = self.journal_id
        superstream.action_confirm()
        values = superstream.prepare_rendering_data()
        for expected_line, saff_line in zip_longest(expected_saff_lines, values[3:]):
            assert expected_line and saff_line, (
                    "%s payslip lines expected by the test, but %s were found in the payslip."
                    % (len(expected_line), len(saff_line.line_ids)))
            self.assertEqual(len(expected_line), len(saff_line),
                "Expected %s Columns but found %s in the payslip." % (len(expected_line), len(saff_line)))
            for expected_val, saff_val, header in zip_longest(expected_line, saff_line, values[2]):
                # print(f"{header}: {expected_val} - {saff_val}")
                self.assertEqual(expected_val, saff_val, "%s was expected but %s is found at header %s!" % (expected_val, saff_val, header))

        # Post Payslip Journal Entries
        superstream.l10n_au_super_stream_lines.payslip_id.move_id._post(False)

        superstream.action_register_super_payment()
        payment_values = [{
            "payment_type": 'outbound',
            "amount": payment_total,
            'destination_account_id': self.account_21400.id
        }]
        self.assertRecordValues(superstream.payment_id, payment_values)

        # Check reconciled
        domain = [('account_id', '=', self.account_21400.id)]
        should_be_reconciled = (superstream.l10n_au_super_stream_lines.payslip_id.move_id.line_ids + superstream.payment_id.move_id.line_ids).filtered_domain(domain)
        self.assertTrue(should_be_reconciled.full_reconcile_id)
        self.assertRecordValues(should_be_reconciled,
                        [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(should_be_reconciled))

    def get_expected_lines(self, super_values: list):
        """Returns values formatted for SAFF file

        Args:
            super_values (list, optional): Requires list of dict with super_guarantee, super_concessional, annual_salary, start_date, end_date.

        Returns:
            list: returns a list of lists where each list represents one line
        """
        lines = []
        for idx, value in enumerate(super_values):
            total = value.get('super_concessional') + value.get('super_guarantee')
            fund = self.super_fund_smsf if value.get('smsf_fund', False) else self.super_fund
            lines.append([idx, "83914571673", "abn", "", "", "", "My Superstream Australian Company", "Gibson", "Mel", "", "mel@test.com", "123456789", "83914571673", "My Superstream Australian Company", "123-456", "12344321",
            "My Superstream Australian Company", fund.abn, "", fund.display_name, "", "DirectDebit", "2023-09-01", "", "", total, fund.bank_account_id.aba_bsb or "", fund.bank_account_id.acc_number or "",
            fund.bank_account_id.partner_id.name or "", "83914571673", "", "My Superstream Australian Company", "", "999999661", "", "",
            "Federer", "Roger", "", "1", "1970-03-21", "RES", "Australian Street", "", "", "", "Sydney", "2000", "NSW", "AU", "roger@gmail.com", "123456789", "123456789", "", "odoo_f47ac10b_001",
            "", "", value.get('start_date'), value.get('end_date'), value.get('super_guarantee'), "", "", value.get('super_concessional'), "", "", "", "", "1975-01-01", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", ""])
        return lines

    def test_00_saff_file_headers(self):
        self.payslips.compute_sheet()
        self.payslips.action_payslip_done()
        superstream = self.payslips._get_superstreams()
        superstream.journal_id = self.journal_id
        superstream.action_confirm()

        values = superstream.prepare_rendering_data()
        header = ["", "1.0", "Negatives Supported", "False", "File ID", "SAFF0000000001"]
        categories = ["Line ID", "Header", "", "", "", "Sender", "", "", "", "", "", "", "Payer", "", "", "", "", "Payee/Receiver", "", "", "", "", "", "", "", "", "", "",
                  "", "Employer", "", "", "", "Super Fund Member Common", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                  "Super Fund Member Contributions", "", "", "", "", "", "", "", "", "", "Super Fund Member Registration", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                  "", "Defined Benefits Contributions", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "SuperDefined Benefit Registration", "", "", "", "", "", "", "", "",
                  "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        details = ["ID", "SourceEntityID", "SourceEntityIDType", "SourceElectronicServiceAddress", "ElectronicErrorMessaging", "ABN", "Organisational Name Text", "Family Name",
                  "Given Name", "Other Given Name", "E-mail Address Text", "Telephone Minimal Number", "ABN", "Organisational Name Text", "BSB Number", "Account Number",
                  "Account Name Text", "ABN", "USI", "Organisational Name Text", "TargetElectronicServiceAddress", "Payment Method Code", "Transaction Date",
                  "Payment/Customer Reference Number", "Bpay Biller Code", "Payment Amount", "BSB Number", "Account Number", "Account Name Text", "ABN", "Location ID",
                  "Organisational Name Text", "Superannuation Fund Generated Employer Identifier", "TFN", "Person Name Title Text", "Person Name Suffix text", "Family Name",
                  "Given Name", "Other Given Name", "Sex Code", "Birth Date", "Address Usage Code", "Address Details Line 1 Text", "Address Details Line 2 Text",
                  "Address Details Line 3 Text", "Address Details Line 4 Text", "Locality Name Text", "Postcode Text", "State or Territory Code", "Country Code",
                  "E-mail Address Text", "Telephone Minimal Number Landline", "Telephone Minimal Number Mobile", "Member Client Identifier", "Payroll Number Identifier",
                  "Employment End Date", "Employment End Reason Text", "Pay Period Start Date", "Pay Period End Date", "Superannuation Guarantee Amount",
                  "Award or Productivity Amount", "Personal Contributions Amount", "Salary Sacrificed Amount", "Voluntary Amount", "Spouse Contributions Amount",
                  "Child Contributions Amount", "Other Third Party Contributions Amount", "Employment Start Date", "At Work Indicator", "Annual Salary for Benefits Amount",
                  "Annual Salary for Contributions Amount", "Annual Salary for Contributions Effective Start Date", "Annual Salary for Contributions Effective End Date",
                  "Annual Salary for Insurance Amount", "Weekly Hours Worked Number", "Occupation Description", "Insurance Opt Out Indicator", "Fund Registration Date",
                  "Benefit Category Text", "Employment Status Code", "Super Contribution Commence Date", "Super Contribution Cease Date",
                  "Member Registration Amendment Reason Text", "Defined Benefit Member Pre Tax Contribution", "Defined Benefit Member Post Tax Contribution",
                  "Defined Benefit Employer Contribution", "Defined Benefit Notional Member Pre Tax Contribution", "Defined Benefit Notional Member Post Tax Contribution",
                  "Defined Benefit Notional Employer Contribution", "Ordinary Time Earnings", "Actual Periodic Salary or Wages Earned", "Superannuable Allowances Paid",
                  "Notional Superannuable Allowances", "Service Fraction", "Service Fraction Effective Date", "Full Time Hours", "Contracted Hours", "Actual Hours Paid",
                  "Employee Location Identifier", "Service Fraction", "Service Fraction Start Date", "Service Fraction End Date", "Defined Benefit Employer Rate",
                  "Defined Benefit Employer Rate Start Date", "Defined Benefit Employer Rate End Date", "Defined Benefit Member Rate", "Defined Benefit Member Rate Start Date",
                  "Defined Benefit Member Rate End Date", "Defined Benefit Annual Salary 1", "Defined Benefit Annual Salary 1 Start Date",
                  "Defined Benefit Annual Salary 1 End Date", "Defined Benefit Annual Salary 2", "Defined Benefit Annual Salary 2 Start Date",
                  "Defined Benefit Annual Salary 2 End Date", "Defined Benefit Annual Salary 3", "Defined Benefit Annual Salary 3 Start Date",
                  "Defined Benefit Annual Salary 3 End Date", "Defined Benefit Annual Salary 4", "Defined Benefit Annual Salary 4 Start Date",
                  "Defined Benefit Annual Salary 4 End Date", "Defined Benefit Annual Salary 5", "Defined Benefit Annual Salary 5 Start Date",
                  "Defined Benefit Annual Salary 5 End Date", "Leave Without Pay Code", "Leave Without Pay Code Start Date", "Leave Without Pay Code End Date",
                  "Annual Salary for Insurance Effective Date", "Annual Salary for Benefits Effective Date", "Employee Status Effective Date",
                  "Employee Benefit Category Effective Date", "Employee Location Identifier", "Employee Location Identifier Start Date", "Employee Location Identifier End Date"]

        self.assertListEqual(values[0][:-1], header[:-1])  # don't compare the sequence number
        self.assertListEqual(values[1], categories)
        self.assertListEqual(values[2], details)

    def test_01_autogenerated_super_stream(self):
        self.payslips.compute_sheet()
        self.payslips.action_payslip_done()
        superstream = self.payslips._get_superstreams()

        expected_lines = self.get_expected_lines([
            {"super_guarantee": 550,
             "super_concessional": 20,
             "start_date": "2023-08-01",
             "end_date": "2023-08-31"},
            {"super_guarantee": 550,
             "super_concessional": 20,
             "start_date": "2023-09-01",
             "end_date": "2023-09-30"}
        ])

        self._test_super_stream(superstream, expected_lines, 1140)

    def test_02_super_stream_manually(self):
        self.payslips.compute_sheet()
        self.payslips.action_payslip_done()

        # Remove autogenerated superstream
        self.payslips._get_superstreams().unlink()

        # Create new superstream
        superstream_form = Form(self.env["l10n_au.super.stream"].with_company(self.australian_company))
        superstream_form.journal_id = self.journal_id
        for payslip in self.payslips:
            with superstream_form.l10n_au_super_stream_lines.new() as line:
                line.payslip_id = payslip
                line.employee_id = payslip.employee_id
                line.sender_id = self.australian_company.l10n_au_hr_super_responsible_id
                line.super_account_id = self.super_account_a

        superstream = superstream_form.save()
        superstream.action_confirm()
        expected_lines = self.get_expected_lines([
            {"super_guarantee": 550,
             "super_concessional": 20,
             "start_date": "2023-08-01",
             "end_date": "2023-08-31"},
            {"super_guarantee": 550,
             "super_concessional": 20,
             "start_date": "2023-09-01",
             "end_date": "2023-09-30"}
        ])

        self._test_super_stream(superstream, expected_lines, 1140)

    def test_03_super_stream_multi_account(self):
        # Set proportion for account A
        self.super_account_a.proportion = 0.4
        # Create another account
        self.env['l10n_au.super.account'].create({
            "date_from": date(2023, 6, 1),
            "employee_id": self.employee.id,
            "fund_id": self.super_fund_smsf.id,
            "proportion": 0.6,
        })

        self.payslips.compute_sheet()
        self.payslips.action_payslip_done()
        superstream = self.payslips._get_superstreams()

        expected_lines = self.get_expected_lines([
            {"super_guarantee": 220,
             "super_concessional": 8,
             "start_date": "2023-08-01",
             "end_date": "2023-08-31"},
            {"super_guarantee": 330,
             "super_concessional": 12,
             "start_date": "2023-08-01",
             "end_date": "2023-08-31",
             "smsf_fund": True},
            {"super_guarantee": 220,
             "super_concessional": 8,
             "start_date": "2023-09-01",
             "end_date": "2023-09-30"},
            {"super_guarantee": 330,
             "super_concessional": 12,
             "start_date": "2023-09-01",
             "end_date": "2023-09-30",
             "smsf_fund": True}
        ])

        self._test_super_stream(superstream, expected_lines, 1140)

    def test_04_super_account_dates(self):
        """ Tests second superaccount with 100% proportion """
        # deactivate account A
        self.super_account_a.account_active = False
        # Create another account for 100% proportion
        self.env['l10n_au.super.account'].create({
            "date_from": date(2023, 9, 1),
            "employee_id": self.employee.id,
            "fund_id": self.super_fund.id,
        })
        slip = self.payslips[1]
        slip.compute_sheet()
        slip.action_payslip_done()
        superstream = slip._get_superstreams()

        expected_lines = self.get_expected_lines([
            {"super_guarantee": 550,
             "super_concessional": 20,
             "start_date": "2023-09-01",
             "end_date": "2023-09-30"}
        ])
        self._test_super_stream(superstream, expected_lines, 570)
