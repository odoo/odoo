# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from odoo.tests import tagged
from odoo.tests.common import Form


@tagged("post_install_l10n", "post_install", "-at_install", "superstream")
class TestPayrollSuperStream(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='au'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Create Super Stream
        cls.australian_company = cls.company_data['company']
        cls.australian_company.write({
            "name": "My Superstream Australian Company",
            "country_id": cls.env.ref("base.au").id,
            "currency_id": cls.env.ref("base.AUD").id,
            "resource_calendar_id": cls.env.ref("l10n_au_hr_payroll.resource_calendar_au_38").id,
            "vat": '83 914 571 673',
        })

        superstream_form = Form(cls.env["l10n_au.super.stream"].with_company(cls.australian_company))

        bank_account = cls.env['res.partner.bank'].create({
            "acc_number": '12344321',
            "acc_type": 'aba',
            "aba_bsb": '123-456',
            "company_id": cls.australian_company.id,
            "partner_id": cls.australian_company.partner_id.id,
        })
        superstream_form.journal_id = cls.env["account.journal"].create({
            "name": "Payslip Bank",
            "type": "bank",
            "aba_fic": "CBA",
            "aba_user_spec": "Test Ltd",
            "aba_user_number": "111111",
            "company_id": cls.australian_company.id,
            "bank_account_id": bank_account.id,
        })
        employee = cls.env['hr.employee'].create({
            'company_id': cls.australian_company.id,
            'resource_calendar_id': cls.australian_company.resource_calendar_id.id,
            'name': 'Roger',
            'work_phone': '123456789',
            'private_street': 'Australian Street',
            'private_city': 'Sydney',
            'birthday':  date(1970, 3, 21),
            'l10n_au_tfn_declaration': 'provided',
            'l10n_au_tfn': '123456789',
            'l10n_au_training_loan': True,
            'l10n_au_nat_3093_amount': 150,
            'l10n_au_child_support_garnishee': 'percentage',
            'l10n_au_child_support_garnishee_amount': 0.1,
            'l10n_au_child_support_deduction': 150,
            'gender': 'male',
        })
        cls.env['hr.contract'].create({
            'company_id': cls.australian_company.id,
            'resource_calendar_id': cls.australian_company.resource_calendar_id.id,
            'employee_id': employee.id,
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
        super_fund = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund A',
            'abn': '2345678912',
            'address_id': cls.env['res.partner'].create({'name': "Fund A Partner"}).id,
        })
        payslip = cls.env['hr.payslip'].create({
            'company_id': cls.australian_company.id,
            'employee_id': employee.id,
            'name': 'Roger Payslip August',
            'date_from': date(2023, 8, 1),
            'date_to': date(2023, 8, 31),
            'input_line_ids': [(5, 0, 0), (0, 0, {'input_type_id': cls.env.ref('hr_payroll.input_child_support').id, 'amount': 200})],
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()

        sender = cls.env["hr.employee"].create({
            "name": "Mel",
            "resource_calendar_id": cls.australian_company.resource_calendar_id.id,
            "company_id": cls.australian_company.id,
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_country_id": cls.env.ref("base.au").id,
            "work_phone": "123456789",
            "birthday": date.today() - relativedelta(years=22),
            # fields modified in the tests
            "marital": "single",
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "12345678",
            "l10n_au_tax_free_threshold": True,
            "is_non_resident": False,
            "l10n_au_training_loan": False,
            "l10n_au_nat_3093_amount": 0,
            "l10n_au_child_support_garnishee_amount": 0,
            "l10n_au_medicare_exemption": "X",
            "l10n_au_medicare_surcharge": "X",
            "l10n_au_medicare_reduction": "X",
            "l10n_au_child_support_deduction": 0,
            "l10n_au_scale": "2",
        })

        with superstream_form.l10n_au_super_stream_lines.new() as line:
            line.employee_id = employee
            line.sender_id = sender
            line.payee_id = super_fund
            line.payslip_id = payslip
        cls.superstream = superstream_form.save()

    def test_rendering_data(self):
        values = self.superstream.prepare_rendering_data()
        header = ["VERSION", "1.0", "Negatives Supported", "False", "File ID", "SAFF0000000001"]
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
        data = [0, "83 914 571 673", "abn", "", "", "", "My Superstream Australian Company", "", "Mel", "", "", "123456789", "83 914 571 673", "My Superstream Australian Company", "123-456", "12344321",
                   "My Superstream Australian Company", "2345678912", "", "Fund A", "", "", "", "", "", "", "", "", "", "83 914 571 673", "", "My Superstream Australian Company", "", "123456789", "", "",
                   "", "Roger", "", "1", "1970-03-21", "RES", "Australian Street", "", "", "", "Sydney", "", "", "", "", "123456789", "", "", "",
                   "", "", "2023-08-01", "2023-08-31", 545.6, "", "", 20.0, "", "", "", "", "1975-01-01", True, "", 60000.0, "", "", "", "", "", "", "", "", "", "", "", "", "",
                   "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                   "", "", "", "", "", "", "", "", ""]

        self.assertListEqual(values[0][:-1], header[:-1])  # don't compare the sequence number
        self.assertListEqual(values[1], categories)
        self.assertListEqual(values[2], details)
        self.assertListEqual(values[3], data)

    def test_superstream_file_action(self):
        self.superstream.action_get_super_stream_file()
