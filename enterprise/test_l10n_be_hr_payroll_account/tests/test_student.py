# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install', '-at_install', 'student')
class TestStudent(AccountTestInvoicingCommon):

    def _validate_payslip(self, payslip, results):
        error = []
        line_values = payslip._get_line_values(results.keys())
        for code, value in results.items():
            payslip_line_value = line_values[code][payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Computed line %s should have an amount = %s instead of %s" % (code, value, payslip_line_value))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    @classmethod
    @AccountTestInvoicingCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()

        cls.new_calendar = cls.env['resource.calendar'].create({
            'name': 'O h/w calendar',
            'company_id': cls.env.company.id,
            'hours_per_day': 9,
            'full_time_required_hours': 0,
            'attendance_ids': [(5, 0, 0)],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Jean-Pol Student',
            'company_id': cls.env.company.id,
            'resource_calendar_id': cls.new_calendar.id,
        })

        cls.contract = cls.env['hr.contract'].create({
            'employee_id': cls.employee.id,
            'company_id': cls.env.company.id,
            'name': 'Jean-Pol Student Contract',
            'state': 'open',
            'date_start': date(2015, 1, 1),
            'resource_calendar_id': cls.new_calendar.id,
            'structure_type_id': cls.env.ref('l10n_be_hr_payroll.structure_type_student').id,
            'wage': 0,
            'hourly_wage': 10.87,
            'fuel_card': 0,
            'meal_voucher_amount': 7.45,
            'representation_fees': 0,
            'commission_on_target': 0,
            'ip_wage_rate': 0,
            'ip': False,
            'transport_mode_private_car': True,
            'distance_home_work': 25,
            'internet': 0,
            'mobile': 0,
        })
        cls.env.invalidate_all()

    def test_student(self):
        # CASE: Worked 6 days
        attendance_work_entry_type = self.env.ref('hr_work_entry.work_entry_type_attendance')
        vals_list = [
            (datetime(2020, 9, 1, 9, 0), datetime(2020, 9, 1, 18, 0)),
            (datetime(2020, 9, 2, 9, 0), datetime(2020, 9, 2, 18, 0)),
            (datetime(2020, 9, 3, 9, 0), datetime(2020, 9, 3, 18, 0)),
            (datetime(2020, 9, 4, 9, 0), datetime(2020, 9, 4, 18, 0)),
            (datetime(2020, 9, 7, 9, 0), datetime(2020, 9, 7, 18, 0)),
            (datetime(2020, 9, 8, 9, 0), datetime(2020, 9, 8, 18, 0)),
        ]
        work_entries = self.env['hr.work.entry'].create([{
            'name': 'Attendance',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': attendance_work_entry_type.id,
            'date_start': vals[0],
            'date_stop': vals[1],
            'company_id': self.env.company.id,
            'state': 'draft',
        } for vals in vals_list])

        payslip = self.env['hr.payslip'].with_context(allowed_company_ids=self.env.company.ids).create({
            'name': 'Test Payslip',
            'employee_id': self.employee.id,
            'date_from': date(2020, 9, 1),
            'date_to': date(2020, 9, 30),
        })

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(payslip.worked_days_line_ids.number_of_hours, 54)
        self.assertEqual(payslip.worked_days_line_ids.number_of_days, 6)

        payslip.compute_sheet()

        self.assertEqual(len(payslip.line_ids), 7)

        payslip_results = {
            'BASIC': 586.98,  # 10.87 * 54 = 586.98
            'ONSS': -15.91,
            'GROSS': 571.07,
            'CAR.PRIV': 13.85,
            'MEAL_V_EMP': -6.54,
            'NET': 578.38,
            'ONSSEMPLOYER': 31.81,
        }
        self._validate_payslip(payslip, payslip_results)
