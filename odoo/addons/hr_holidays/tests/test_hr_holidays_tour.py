# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import HttpCase
from odoo.tests.common import tagged

from datetime import date


@tagged('post_install', '-at_install')
class TestHrHolidaysTour(HttpCase):
    @freeze_time('01/17/2022')
    def test_hr_holidays_tour(self):
        admin_user = self.env.ref('base.user_admin')
        admin_employee = admin_user.employee_id
        HRLeave = self.env['hr.leave']
        date_from = date(2022, 1, 17)
        date_to = date(2022, 1, 18)
        leaves_on_freeze_date = HRLeave.search([
            ('date_from', '>=', date_from),
            ('date_to', "<=", date_to),
            ('employee_id', '=', admin_employee.id)
        ])
        leaves_on_freeze_date.sudo().unlink()

        LeaveType = self.env['hr.leave.type'].with_user(admin_user)

        holidays_type_1 = LeaveType.create({
            'name': 'NotLimitedHR',
            'requires_allocation': 'no',
            'leave_validation_type': 'hr',
        })
        # add allocation
        self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': admin_employee.id,
            'holiday_status_id': holidays_type_1.id,
            'number_of_days': 1,
            'state': 'confirm',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
        })

        self.start_tour('/web', 'hr_holidays_tour', login="admin")

    def test_hr_holidays_launch(self):
        admin_user = self.env.ref("base.user_admin")
        self.env.ref("base.lang_sr@latin").active = True
        admin_user.lang = "sr@latin"
        self.start_tour("/web", "hr_holidays_launch", login="admin")
