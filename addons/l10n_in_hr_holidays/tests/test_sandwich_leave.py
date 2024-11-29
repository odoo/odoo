# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.tests import tagged, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSandwichLeave(TransactionCase):

    def setUp(self):
        super().setUp()
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'l10n_in_is_sandwich_leave': True,
        })

        self.rahul_emp = self.env['hr.employee'].create({
            'name': 'Rahul',
            'country_id': self.env.ref('base.in').id,
        })

    def test_sandwich_leave(self):
        with freeze_time('2023-08-15'):
            public_holiday = self.env['resource.calendar.leaves'].create({
                'name': 'Independence Day',
                'date_from': '2023-08-15',
                'date_to': '2023-08-15',
                'resource_id': False,
                'company_id': self.env.company.id,
            })
            before_holiday_leave = self.env['hr.leave'].create({
                'name': 'Test Leave',
                'employee_id': self.rahul_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': "2023-08-14",
                'request_date_to': "2023-08-14",
            })
            employee_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', self.rahul_emp.id),
                ('state', 'not in', ['cancel', 'refuse']),
                ('leave_type_request_unit', '=', 'day'),
            ])
            after_holiday_leave = self.env['hr.leave'].create({
                'name': 'Test Leave',
                'employee_id': self.rahul_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': "2023-08-16",
                'request_date_to': "2023-08-16",
            })

            leave = before_holiday_leave._l10n_in_apply_sandwich_rule(public_holiday, employee_leaves)
            self.assertEqual(leave, 1, "The total leaves should be 1")
            sandwiched_leave = after_holiday_leave._l10n_in_apply_sandwich_rule(public_holiday, employee_leaves)
            self.assertEqual(sandwiched_leave, 2, "The total leaves should be 2 including sandwich leave")
