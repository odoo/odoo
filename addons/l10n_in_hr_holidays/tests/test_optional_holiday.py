# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests import tagged, Form
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOptionalHoliday(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.country_id = cls.env.ref('base.in').id
        cls.env.user.tz = 'Asia/Kolkata'

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Indian Leave Type',
            'requires_allocation': 'no',
            'time_type': 'leave',
            'request_unit': 'hour',
            'l10n_in_is_limited_to_optional_days': True
        })

        cls.optional_holiday = cls.env['l10n.in.hr.leave.optional.holiday'].create({
            'name': 'optional holiday',
            'date': (datetime.today() + timedelta(days=1)).date()
        })

    def test_optional_holiday_valid_leave_request(self):
        with Form(self.env['hr.leave'].with_context(default_employee_id=self.employee_emp_id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = (datetime.today() + timedelta(days=1)).date()
            leave_form.request_date_to = (datetime.today() + timedelta(days=1)).date()

    def test_optional_holiday_invalid_leave_request(self):
        with self.assertRaises(ValidationError):
            with Form(self.env['hr.leave'].with_context(default_employee_id=self.employee_hruser_id)) as leave_form:
                leave_form.holiday_status_id = self.leave_type
                leave_form.request_date_from = datetime.today().date()
                leave_form.request_date_to = datetime.today().date()
