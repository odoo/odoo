# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta

from freezegun import freeze_time

from odoo import fields
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged, users, warmup
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install", "out_of_office")
class TestOutOfOffice(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': False,
        })

    @freeze_time('2024-06-06')
    def test_leave_ooo(self):
        self.assertNotEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should not be on leave')
        self.assertNotEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should not be on leave')
        # validate a leave from 2024-06-05 (Wednesday) to 2024-06-07 (Friday)
        first_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2024-06-05",
            'request_date_to': "2024-06-07",
        })
        first_leave.action_approve()
        # validate a leave from 2024-06-10 (Monday) to 2024-06-11 (Tuesday)
        second_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': "2024-06-10",
            'request_date_to': "2024-06-11",
        })
        second_leave.action_approve()
        # missing dependencies on compute functions
        self.employee_hruser.user_id.invalidate_recordset(["im_status"])
        self.employee_hruser.user_id.partner_id.invalidate_recordset(["im_status"])
        self.assertEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should be out (leave_offline)')
        self.assertEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should be out (leave_offline)')

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
        data = Store().add(channel).get_result()
        partner_info = next(p for p in data["res.partner"] if p["id"] == partner.id)
        partner2_info = next(p for p in data["res.partner"] if p["id"] == partner2.id)
        user_info = next(u for u in data["res.users"] if u["id"] == partner_info["main_user_id"])
        user2_info = next(u for u in data["res.users"] if u["id"] == partner2_info["main_user_id"])
        employee_info = next(e for e in data["hr.employee"] if e["id"] == user_info["employee_ids"][0])
        employee2_info = next(e for e in data["hr.employee"] if e["id"] == user2_info["employee_ids"][0])
        self.assertFalse(employee2_info["leave_date_to"], "current user should not be out of office")
        # The employee will be back in the office the day after his second leave ends
        self.assertEqual(
            employee_info["leave_date_to"], "2024-06-12", "correspondent should be out of office"
        )
        self.assertEqual(
            self.employee_hruser.user_id.with_context(formatted_display_name=True).display_name,
            'armande (base.group_user,hr_holidays.group_hr_holidays_user) \t ✈ --Back on Jun 12, 2024--',
            'formatted display name should show the "Back on" formatted date'
        )


@tagged('out_of_office')
class TestOutOfOfficePerformance(TestHrHolidaysCommon, TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestOutOfOfficePerformance, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': False,
        })
        cls.leave_date_end = (datetime.today() + relativedelta(days=2))
        cls.leave = cls.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': cls.employee_hruser_id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_from': (date.today() - relativedelta(days=1)),
            'request_date_to': cls.leave_date_end,
        })

        cls.hr_user = cls.employee_hruser.user_id
        cls.hr_partner = cls.employee_hruser.user_id.partner_id
        cls.employer_partner = cls.user_employee.partner_id

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_offline(self):
        with self.assertQueryCount(__system__=4, demo=4):
            self.assertEqual(self.employer_partner.im_status, 'offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_user_leave_offline(self):
        self.leave.write({'state': 'validate'})
        with self.assertQueryCount(__system__=2, demo=2):
            self.assertEqual(self.hr_user.im_status, 'leave_offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_leave_offline(self):
        self.leave.write({'state': 'validate'})
        with self.assertQueryCount(__system__=4, demo=4):
            self.assertEqual(self.hr_partner.im_status, 'leave_offline')

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
