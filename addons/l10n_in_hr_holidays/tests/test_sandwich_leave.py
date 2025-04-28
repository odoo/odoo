# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.tests import tagged, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSandwichLeave(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_india = cls.env['res.company'].create({
            'name': "Indian Company",
            'country_id': cls.env.ref('base.in').id,
        })
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company_india.ids))
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'l10n_in_is_sandwich_leave': True,
        })

        cls.rahul_emp = cls.env['hr.employee'].create({
            'name': 'Rahul',
            'country_id': cls.env.ref('base.in').id,
        })

        cls.wednesday_public_holiday = cls.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2025-01-29 00:00:00',
            'date_to': '2025-01-29 23:59:59',
            'resource_id': False,
        })

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_monday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-20",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 4)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_monday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-20",
        })
        # print(holiday_leave.l10n_in_contains_sandwich_leaves, holiday_leave.number_of_days)
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_sunday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_sunday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-18",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_sunday(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-19",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_3days_with_public_holidays(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-30",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 3)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_start_with_public_holidays(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_stop_with_public_holidays(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-30",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_public_holidays(self):
        self.env.company = self.company_india
        self.env.companies = self.company_india
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    def test_sandwich_in_two_part_1(self):
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
            self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
            self.assertEqual(before_holiday_leave.number_of_days, 1)
            self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
            self.assertEqual(after_holiday_leave.number_of_days, 2)

    def test_sandwich_in_two_part_2(self):
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
                'request_date_from': "2023-08-16",
                'request_date_to': "2023-08-16",
            })
            after_holiday_leave = self.env['hr.leave'].create({
                'name': 'Test Leave',
                'employee_id': self.rahul_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': "2023-08-14",
                'request_date_to': "2023-08-14",
            })
            self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
            self.assertEqual(before_holiday_leave.number_of_days, 1)
            self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
            self.assertEqual(after_holiday_leave.number_of_days, 2)
