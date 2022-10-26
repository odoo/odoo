# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged, users, warmup
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('out_of_office')
class TestOutOfOffice(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': 'no',
        })

    def test_leave_ooo(self):
        self.assertNotEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should not be on leave')
        self.assertNotEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should not be on leave')
        leave_date_end = (datetime.today() + relativedelta(days=3))
        leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': leave_date_end,
            'number_of_days': 4,
        })
        leave.action_approve()
        self.assertEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should be out (leave_offline)')
        self.assertEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should be out (leave_offline)')

        partner = self.employee_hruser.user_id.partner_id
        partner2 = self.user_employee.partner_id

        channel = self.env['mail.channel'].with_user(self.user_employee).with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
        }).create({
            'channel_partner_ids': [(4, partner.id), (4, partner2.id)],
            'channel_type': 'chat',
            'name': 'test'
        })
        channel_info = channel.channel_info()[0]
        # shape of channelMembers is [('insert', data...)], [0][1] accesses the data
        members_data = channel_info['channel']['channelMembers'][0][1]
        self.assertEqual(len(members_data), 2, "Channel info should get info for the 2 members")
        partner_info = next(member for member in members_data if member['persona']['partner']['email'] == partner.email)
        partner2_info = next(member for member in members_data if member['persona']['partner']['email'] == partner2.email)
        self.assertFalse(partner2_info['persona']['partner']['out_of_office_date_end'], "current user should not be out of office")
        self.assertEqual(partner_info['persona']['partner']['out_of_office_date_end'], leave_date_end.strftime(DEFAULT_SERVER_DATE_FORMAT), "correspondent should be out of office")


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
        cls.leave_date_end = (datetime.today() + relativedelta(days=3))
        cls.leave = cls.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': cls.employee_hruser_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days': 4,
        })

        cls.hr_user = cls.employee_hruser.user_id
        cls.hr_partner = cls.employee_hruser.user_id.partner_id
        cls.employer_partner = cls.user_employee.partner_id

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_offline(self):
        with self.assertQueryCount(__system__=2, demo=2):
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
        with self.assertQueryCount(__system__=2, demo=2):
            self.assertEqual(self.hr_partner.im_status, 'leave_offline')
