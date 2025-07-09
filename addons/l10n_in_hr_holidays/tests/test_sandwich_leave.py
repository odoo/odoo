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
        cls.leave_type, cls.leave_type_1 = cls.env['hr.leave.type'].create([{
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'l10n_in_is_sandwich_leave': True,
        }, {
            'name': 'Test Leave Type 2',
            'request_unit': 'half_day',
            'l10n_in_is_sandwich_leave': True,
        }])
        cls.rahul_emp = cls.env['hr.employee'].create({
            'name': 'Rahul',
            'country_id': cls.env.ref('base.in').id,
            'company_id': cls.company_india.id,
        })
        cls.wednesday_public_holiday = cls.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2025-01-29 00:00:00',
            'date_to': '2025-01-29 23:59:59',
            'resource_id': False,
        })

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_monday(self):
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
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-20",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_sunday(self):
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
    def test_sandwich_leave_2days_stop_with_public_holidays(self):
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
    def test_sandwich_leave_2days_start_with_public_holidays(self):
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
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_weeks(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-02-01",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 12)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_1(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-30",
            'request_date_to': "2025-01-30",
        })

        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_2(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-30",
            'request_date_to': "2025-01-30",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_weeks_in_two(self):
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-02-01",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 5)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 7)

    @freeze_time('2025-01-15')
    def test_sandwich_for_two_leave_type(self):
        """
            --working days: 24th and 27th January
            --non-working days: 25th, 26th January
        """
        other_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'request_unit': 'day',
        })
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': other_leave_type.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-01-27",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertFalse(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 1)

        # checking for different leave type with sandwich set as True
        other_leave_type.l10n_in_is_sandwich_leave = True
        leave_duration_dict = after_holiday_leave._get_durations()
        self.assertEqual(leave_duration_dict[after_holiday_leave.id][0], 3)
