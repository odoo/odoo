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
            'requires_allocation': 'no',
        })

    @freeze_time('2024-06-06')
    def test_leave_ooo(self):
        self.assertNotEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should not be on leave')
        self.assertNotEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should not be on leave')
        first_leave_date_end = (date.today() + relativedelta(days=1))
        first_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': (date.today() - relativedelta(days=1)),
            'request_date_to': first_leave_date_end,
        })
        first_leave.action_approve()
        # validate a leave from 2024-06-5 (Wednesday) to 2024-06-07 (Friday)
        second_leave_date_end = (date.today() + relativedelta(days=5))
        second_leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': (date.today() + relativedelta(days=4)),
            'request_date_to': second_leave_date_end,
        })
        second_leave.action_approve()
        # validate a leave from 2024-06-10 (Monday) to 2024-06-11 (Tuesday)
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
        data = Store(channel).get_result()
        partner_info = next(p for p in data["res.partner"] if p["id"] == partner.id)
        partner2_info = next(p for p in data["res.partner"] if p["id"] == partner2.id)
        self.assertFalse(
            partner2_info["out_of_office_date_end"], "current user should not be out of office"
        )
        # The employee will be back in the office the day after his second leave ends
        self.assertEqual(
            partner_info["out_of_office_date_end"],
            fields.Date.to_string(second_leave_date_end + relativedelta(days=1)),
            "correspondent should be out of office",
        )


@tagged('out_of_office')
class TestOutOfOfficePerformance(TestHrHolidaysCommon, TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestOutOfOfficePerformance, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': 'no',
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
        with self.assertQueryCount(__system__=3, demo=3):
            self.assertEqual(self.employer_partner.im_status, 'offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_user_leave_offline(self):
        self.leave.write({'state': 'validate'})
        with self.assertQueryCount(__system__=3, demo=3):
            self.assertEqual(self.hr_user.im_status, 'leave_offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_leave_offline(self):
        self.leave.write({'state': 'validate'})
        with self.assertQueryCount(__system__=3, demo=3):
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
