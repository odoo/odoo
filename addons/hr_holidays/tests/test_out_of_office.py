# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta

from freezegun import freeze_time

from odoo import Command
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged, users, warmup
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install", "out_of_office")
class TestOutOfOffice(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Legal Leaves',
            'code': 'Legal Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

    @freeze_time('2024-06-06')
    def test_leave_ooo(self):
        self.assertFalse(self.employee_hruser.leave_date_to, 'user should not be on leave')
        # validate a leave from 2024-06-05 (Wednesday) to 2024-06-07 (Friday)
        first_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': "2024-06-05",
            'request_date_to': "2024-06-07",
        })
        first_leave.action_approve()
        # validate a leave from 2024-06-10 (Monday) to 2024-06-11 (Tuesday)
        second_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': "2024-06-10",
            'request_date_to': "2024-06-11",
        })
        second_leave.action_approve()
        # missing dependencies on compute functions
        self.employee_hruser.invalidate_recordset(["leave_back_datetime", "leave_date_to"])

        partner = self.employee_hruser.user_id.partner_id
        partner2 = self.user_employee.partner_id

        channel = self.env['discuss.channel'].with_user(self.user_employee).with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
        }).create({
            'channel_partner_ids': [(4, partner.id), (4, partner2.id)],
            'channel_type': 'chat',
            'name': 'test'
        })
        data = Store().add(channel, "_store_channel_fields")._build_result()
        partner_info = next(p for p in data["res.partner"] if p["id"] == partner.id)
        partner2_info = next(p for p in data["res.partner"] if p["id"] == partner2.id)
        user_info = next(u for u in data["res.users"] if u["id"] == partner_info["main_user_id"])
        user2_info = next(u for u in data["res.users"] if u["id"] == partner2_info["main_user_id"])
        employee_info = next(e for e in data["hr.employee"] if e["id"] == user_info["all_employee_ids"][0])
        employee2_info = next(e for e in data["hr.employee"] if e["id"] == user2_info["all_employee_ids"][0])
        self.assertFalse(employee2_info["leave_date_to"], "current user should not be out of office")
        # The employee will be back in the office the day after his second leave ends
        self.assertEqual(
            employee_info["leave_date_to"], "2024-06-12", "correspondent should be out of office"
        )
        # 8:00 in Brussels
        self.assertEqual(employee_info["leave_back_datetime"], "2024-06-12 06:00:00")
        self.assertEqual(
            self.employee_hruser.user_id.with_context(formatted_display_name=True).display_name,
            'armande (base.group_user,hr_holidays.group_hr_holidays_user) !!✈ Back on Jun 12, 2024!!',
            'formatted display name should show the "Back on" formatted date'
        )

    @freeze_time('2024-06-06 08:00:00')
    def test_leave_ooo_half_day(self):
        half_day_type = self.env['hr.work.entry.type'].create({
            'name': 'Half Day Leaves',
            'code': 'Half Day Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'half_day',
        })
        # validate the morning of 2024-06-06 (Thursday), the employee is back after the lunch
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': half_day_type.id,
            'request_date_from': "2024-06-06",
            'request_date_to': "2024-06-06",
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        })
        leave.action_approve()
        self.employee_hruser.invalidate_recordset(["leave_back_datetime", "leave_date_to"])
        self.assertEqual(self.employee_hruser.leave_date_to, date(2024, 6, 6))
        # 13:00 in Brussels
        self.assertEqual(self.employee_hruser.leave_back_datetime, datetime(2024, 6, 6, 11, 0))
        user = self.employee_hruser.user_id
        self.assertEqual(
            user.with_context(formatted_display_name=True, tz='Europe/Brussels').display_name,
            'armande (base.group_user,hr_holidays.group_hr_holidays_user) !!✈ Back at 01:00 PM!!',
        )
        self.assertEqual(
            user.with_context(formatted_display_name=True, tz='Asia/Kolkata').display_name,
            'armande (base.group_user,hr_holidays.group_hr_holidays_user) !!✈ Back at 04:30 PM!!',
            'the return time is shown in the timezone of the reader',
        )

    @freeze_time('2024-06-06 08:00:00')
    def test_leave_ooo_half_day_duration_calendar(self):
        self.employee_hruser.resource_calendar_id = self.env['resource.calendar'].create({
            'name': '8 hours a day',
            'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(dayofweek), 'duration_hours': 8})
                for dayofweek in range(5)
            ],
        })
        half_day_type = self.env['hr.work.entry.type'].create({
            'name': 'Half Day Leaves',
            'code': 'Half Day Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'half_day',
        })
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': half_day_type.id,
            'request_date_from': "2024-06-06",
            'request_date_to': "2024-06-06",
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        })
        leave.action_approve()
        self.employee_hruser.invalidate_recordset(["leave_back_datetime", "leave_date_to"])
        # the rest of the day is still worked
        self.assertEqual(self.employee_hruser.leave_date_to, date(2024, 6, 6))
        # 12:00 in Brussels
        self.assertEqual(self.employee_hruser.leave_back_datetime, datetime(2024, 6, 6, 10, 0))

    @freeze_time('2024-06-06 12:00:00')
    def test_leave_ooo_custom_hours(self):
        hour_type = self.env['hr.work.entry.type'].create({
            'name': 'Hour Leaves',
            'code': 'Hour Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': hour_type.id,
            'request_date_from': "2024-06-06",
            'request_date_to': "2024-06-06",
            'request_hour_from': 13,
            'request_hour_to': 15,
        })
        leave.action_approve()
        self.employee_hruser.invalidate_recordset(["leave_back_datetime", "leave_date_to"])
        # the rest of the afternoon is still worked
        self.assertEqual(self.employee_hruser.leave_date_to, date(2024, 6, 6))
        # 15:00 in Brussels, in the middle of the afternoon attendance
        self.assertEqual(self.employee_hruser.leave_back_datetime, datetime(2024, 6, 6, 13, 0))

    def test_first_working_interval_independent_of_batch(self):
        # 09:00 and 08:30 in Brussels, both during the morning attendance
        employees = self.employee_hruser | self.employee_hrmanager
        result = employees._get_first_working_interval_batch({
            self.employee_hruser.id: datetime(2024, 6, 6, 7, 0),
            self.employee_hrmanager.id: datetime(2024, 6, 6, 6, 30),
        })
        self.assertEqual(result[self.employee_hruser.id], datetime(2024, 6, 6, 7, 0))
        self.assertEqual(result[self.employee_hrmanager.id], datetime(2024, 6, 6, 6, 30))

    @freeze_time('2024-06-04')
    def test_leave_ooo_batched(self):
        self.assertFalse(self.employee_emp.leave_date_to, 'first employee should not be on leave')
        self.assertFalse(self.employee_hruser.leave_date_to, 'second employee should not be on leave')
        employees = self.employee_emp | self.employee_hruser
        leaves = self.env['hr.leave'].create([{
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': "2024-06-03",
            'request_date_to': "2024-06-06",
        }, {
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': "2024-06-02",
            'request_date_to': "2024-06-05",
        }])
        leaves.write({'state': 'validate'})
        employees.invalidate_recordset(["leave_date_to"])
        self.assertEqual(employees.mapped("leave_date_to"), [date(2024, 6, 7), date(2024, 6, 6)])

    @freeze_time('2024-06-04')
    def test_leave_status_without_hr_access(self):
        """ The leave status is read by every internal user: it feeds the
        presence icon and the avatar card of its colleagues. Computing it must
        not require the officer access of the employee versions.
        """
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': "2024-06-03",
            'request_date_to': "2024-06-05",
        })
        leave.action_approve()

        self.env.invalidate_all()
        employee = self.employee_hruser.with_user(self.user_employee)
        self.assertFalse(
            employee.has_field_access(employee._fields['version_ids'], 'read'),
            "an employee is not an officer: the versions stay out of reach")
        self.assertTrue(employee.leave_date_to, "a colleague reads when the employee is back")
        self.assertEqual(employee.hr_icon_display, 'presence_holiday_absent')

    @freeze_time("2024-06-05")
    def test_public_holiday_ooo(self):
        self.assertFalse(self.employee_hruser.leave_date_to, "user should not be on leave")
        self.env["resource.calendar.leaves"].create({
            "name": "Public Holiday",
            "resource_id": False,
            "company_id": self.employee_hruser.company_id.id,
            "date_from": datetime(2024, 6, 5, 0, 0, 0),
            "date_to": datetime(2024, 6, 5, 23, 59, 59),
        })
        employee = self.employee_hruser
        employee.invalidate_recordset(["leave_date_to"])
        self.assertTrue(employee.leave_date_to, "correspondent should be back on office after the public holiday")
        user = employee.user_id
        user.invalidate_recordset(["leave_date_to"])
        self.assertTrue(user.leave_date_to, "correspondent should be back on office after the public holiday")


@tagged('out_of_office')
@tagged('at_install', '-post_install')  # LEGACY at_install, fails post install
class TestOutOfOfficePerformance(TestHrHolidaysCommon, TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestOutOfOfficePerformance, cls).setUpClass()
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Legal Leaves',
            'code': 'Legal Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.leave_date_end = (datetime.today() + relativedelta(days=2))
        cls.leave = cls.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': cls.employee_hruser_id,
            'work_entry_type_id': cls.work_entry_type.id,
            'request_date_from': (date.today() - relativedelta(days=1)),
            'request_date_to': cls.leave_date_end,
        })

        cls.hr_user = cls.employee_hruser.user_id
        cls.hr_partner = cls.employee_hruser.user_id.partner_id
        cls.employer_partner = cls.user_employee.partner_id

    def test_search_absent_employee(self):
        present_employees = self.env['hr.employee'].search([('is_absent', '!=', True)])
        absent_employees = self.env['hr.employee'].search([('is_absent', '=', True)])
        today_date = datetime.now(timezone.utc).date()
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('state', '=', 'validate'),
            ('date_from', '<=', today_date),
            ('date_to', '>=', today_date),
        ])
        for employee in present_employees:
            self.assertFalse(employee in holidays.employee_id)
        for employee in absent_employees:
            self.assertFalse(employee not in holidays.employee_id)
