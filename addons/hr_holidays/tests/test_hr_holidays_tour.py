# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import HttpCase
from odoo.tests.common import tagged
from odoo.addons.hr.tests.test_utils import get_admin_employee

from datetime import date


@tagged('post_install', '-at_install')
class TestHrHolidaysTour(HttpCase):
    @freeze_time('01/17/2022')
    def test_hr_holidays_tour(self):
        admin_user = self.env.ref('base.user_admin')
        admin_user.write({
            'email': 'mitchell.admin@example.com',
        })
        admin_employee = get_admin_employee(self.env)
        HRLeave = self.env['hr.leave']
        date_from = date(2022, 1, 17)
        date_to = date(2022, 1, 18)
        leaves_on_freeze_date = HRLeave.search([
            ('date_from', '>=', date_from),
            ('date_to', "<=", date_to),
            ('employee_id', '=', admin_employee.id)
        ])
        leaves_on_freeze_date.sudo().unlink()

        HrWorkEntryType = self.env['hr.work.entry.type'].with_user(admin_user)

        holidays_type_1 = HrWorkEntryType.create({
            'name': 'NotLimitedHR',
            'code': 'NotLimitedHR',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'count_as': 'absence',
        })
        # add allocation
        self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': admin_employee.id,
            'work_entry_type_id': holidays_type_1.id,
            'number_of_days': 1,
            'state': 'confirm',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
        })

        self.start_tour('/odoo', 'hr_holidays_tour', login="admin")

    def test_time_off_card_new_request(self):
        """
        Ensures that the `new request` link from the Time Off cards in the dashboard
        only appears when the related time off allows allocation requests from employees
        """
        user = mail_new_test_user(self.env, login='test', groups='hr_holidays.group_hr_holidays_employee')
        employee = self.env['hr.employee'].create({'name': 'No Time Off Rights', 'user_id': user.id})
        work_entry_types = self.env['hr.work.entry.type'].create([
            {
                'name': 'Allocation Requests Allowed',
                'code': 'AllocationRequestsAllowed',
                'requires_allocation': True,
                'employee_requests': True,
                'request_unit': 'day',
                'unit_of_measure': 'day',
                'count_as': 'absence',
            }, {
                'name': 'Allocation Requests Forbidden',
                'code': 'AllocationRequestsForbidden',
                'requires_allocation': True,
                'employee_requests': False,
                'request_unit': 'day',
                'unit_of_measure': 'day',
                'count_as': 'absence',
            },
        ])
        self.env['hr.leave.allocation'].create([{
            'name': f'Allocation {work_entry_type.name}',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_days': 1,
            'state': 'confirm',
        } for work_entry_type in work_entry_types])._action_validate()

        self.start_tour('/odoo', 'time_off_card_new_request', login="test")
