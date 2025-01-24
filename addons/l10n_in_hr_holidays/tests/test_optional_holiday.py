# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon

from datetime import datetime, timedelta

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOptionalHoliday(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.country_id = cls.env.ref('base.in').id
        cls.env.company = cls.company
        cls.env.user.tz = 'Asia/Kolkata'

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Indian Leave Type',
            'requires_allocation': 'no',
            'time_type': 'leave',
            'request_unit': 'hour',
            'l10n_in_is_limited_to_optional_days': True
        })

        cls.optional_holiday_1, cls.optional_holiday_2 = cls.env['l10n.in.hr.leave.optional.holiday'].create([{
            'name': 'optional holiday 1',
            'date': (datetime.today() + timedelta(days=1)).date()
        }, {
            'name': 'optional holiday 2',
            'date': (datetime.today() - timedelta(days=1)).date()
        }])

    def test_optional_holiday_full_day_leave(self):
        with Form(self.env['hr.leave'].with_context(default_employee_id=self.employee_emp_id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.l10n_in_optional_day_id = self.optional_holiday_1
            self.assertEqual(leave_form.request_date_from, self.optional_holiday_1.date)
            self.assertEqual(leave_form.request_date_to, self.optional_holiday_1.date)

    def test_optional_holiday_half_day_leave(self):
        with Form(self.env['hr.leave'].with_context(default_employee_id=self.employee_hruser_id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.l10n_in_optional_day_id = self.optional_holiday_2
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'pm'
            self.assertEqual(leave_form.request_date_from, self.optional_holiday_2.date)
            self.assertEqual(leave_form.request_date_to, self.optional_holiday_2.date)
            self.assertEqual(leave_form.request_date_from_period, 'pm')

    def test_optional_holiday_hours_leave(self):
        with Form(self.env['hr.leave'].with_context(default_employee_id=self.employee_hrmanager_id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.l10n_in_optional_day_id = self.optional_holiday_1
            leave_form.request_unit_hours = True
            leave_form.request_hour_from = 8
            leave_form.request_hour_to = 17
            self.assertEqual(leave_form.request_date_from, self.optional_holiday_1.date)
            self.assertEqual(leave_form.request_date_to, self.optional_holiday_1.date)
            self.assertEqual(leave_form.request_unit_hours, True)
            self.assertEqual(leave_form.request_hour_from, 8)
            self.assertEqual(leave_form.request_hour_to, 17)
