# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOptionalHoliday(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.country_id = cls.env.ref('base.in').id
        cls.env.user.tz = 'Asia/Kolkata'

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Indian Leave Type',
            'code': 'Indian Leave Type',
            'requires_allocation': False,
            'count_as': 'absence',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
            'l10n_in_is_limited_to_optional_days': True,
        })

        cls.optional_holiday = cls.env['l10n.in.hr.leave.optional.holiday'].create({
            'name': 'optional holiday',
            'date': '2025-01-02',
        })

    def test_optional_holiday_valid_leave_request(self):
        leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'employee_id': self.employee_emp_id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': '2025-01-02',
            'request_date_to': '2025-01-02',
        })
        self.assertTrue(leave.id)

    def test_optional_holiday_invalid_leave_request(self):
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create({
                'employee_id': self.employee_hruser_id,
                'work_entry_type_id': self.work_entry_type.id,
                'request_date_from': '2025-01-03',
                'request_date_to': '2025-01-03',
            })
