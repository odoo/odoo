# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY

from odoo.tests import tagged

from .common import TestL10NHkHrPayrollAccountCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentInLieuOfNotice(TestL10NHkHrPayrollAccountCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='hk'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.work_contact = cls.env['res.partner'].create([{
            'name': "Test Employee",
            'company_id': cls.env.company.id,
        }])

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_contact_id': cls.work_contact.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.hk').id,
            'marital': "single",
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_hk_hr_payroll.structure_type_employee_cap57').id,
            'date_start': date(2022, 1, 1),
            'date_end': date(2023, 4, 21),
            'wage': 20000.0,
            'l10n_hk_internet': 200.0,
            'state': "close",
        })

    def test_regular(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20200.0,
            'NET': 20200.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_lieu_of_notice_period(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
            input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_lieu_of_notice_period').id, 'amount': 2})])
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 40400.0,
            'NET': 40400.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_incomplete_year(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2023, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20480.56,
            'NET': 20480.56,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_commission(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31),
                                             input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 30200.0,
            'NET': 30200.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_unpaid_and_non_full_pay_leave(self):
        leaves_to_create = [
            (datetime(2023, 2, 21), datetime(2023, 2, 22), 'l10n_hk_hr_payroll.holiday_type_hk_unpaid_leave'),
            (datetime(2023, 3, 13), datetime(2023, 3, 15), 'l10n_hk_hr_payroll.holiday_type_hk_sick_leave_80'),
        ]
        for leave in leaves_to_create:
            self._generate_leave(leave[0], leave[1], leave[2])
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20195.12,
            'NET': 20195.12,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)
