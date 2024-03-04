# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tests.tagged('post_install', '-at_install')
class TestHrHolidaysAccessRightsCommon(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysAccessRightsCommon, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({'name': 'Test company 2'})

    def test_unrelated_public_leave(self):
        public_leave = self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off for Company 2',
            'resource_id': False,
            'date_from': datetime(2024, 1, 3, 6, 0, 0),
            'date_to': datetime(2024, 1, 3, 19, 0, 0),
        })
        public_leave.company_id = self.company_2
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': 'no',
            'request_unit': 'day',
            'company_id': False,
        })
        leave = self.env['hr.leave'].create({
            'name': '3 days leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2024, 1, 2),
            'request_date_to': datetime(2024, 1, 4),
        })
        self.assertNotEqual(public_leave.company_id, self.employee_emp.company_id)
        self.assertEqual(
            leave.number_of_days, 3,
            "The leave should not depend on other companies public leaves.")
