from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestExceptionalDayLeave(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_india = cls.env['res.company'].create({
            'name': "Indian Company",
            'country_id': cls.env.ref('base.in').id,
        })
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company_india.ids))
        cls.Leave = cls.env['hr.leave']
        cls.employee = cls.env['hr.employee'].create({'name': 'Test Employee'})

        cls.exceptional_day_1 = cls.env['l10n.in.hr.holiday.exceptional.day'].create({
            'name': 'Exceptional Day',
            'start_date': '2025-02-08',
            'end_date': '2025-02-09',
            'company_id': cls.company_india.id,
        })

        cls.exceptional_day_2 = cls.env['l10n.in.hr.holiday.exceptional.day'].create({
            'name': 'Test Exceptional Day',
            'start_date': '2025-02-15',
            'end_date': '2025-02-15',
            'company_id': cls.company_india.id,
        })

        cls.wednesday_public_holiday = cls.env['resource.calendar.leaves'].create({
            'name': 'Test public holiday',
            'date_from': '2025-02-14 00:00:00',
            'date_to': '2025-02-14 23:59:59',
            'resource_id': False,
        })

    def test_leave_on_one_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-08',
            'request_date_to': '2025-02-08',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 1, "Leave duration should be 1 day")

    def test_leave_on_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-08',
            'request_date_to': '2025-02-09',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 2, "Leave duration should be 2 days")

    def test_leave_stops_with_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-07',
            'request_date_to': '2025-02-08',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 2, "Leave duration should be 2 days")

    def test_leave_starts_with_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-08',
            'request_date_to': '2025-02-10',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 3, "Leave duration should be 3 days")

    def test_leave_covering_exceptional_days(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-07',
            'request_date_to': '2025-02-10',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 4, "Leave duration should be 2 days")

    def test_leave_public_holiday_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-14',
            'request_date_to': '2025-02-15',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 1, "Leave duration should be 1 day")

    def test_leave_covering_public_holiday_exceptional_day(self):
        leave = self.Leave.create({
            'employee_id': self.employee.id,
            'request_date_from': '2025-02-13',
            'request_date_to': '2025-02-15',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id
        })
        self.assertEqual(leave.number_of_days, 2, "Leave duration should be 2 days")

    def test_exceptional_day_on_public_holiday(self):
        with self.assertRaises(UserError):
            self.env['l10n.in.hr.holiday.exceptional.day'].create({
                'name': 'Exceptional Day on Public Holiday',
                'start_date': '2025-02-14',
                'end_date': '2025-02-14',
                'company_id': self.company_india.id,
            })
