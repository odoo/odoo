# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import tagged, users, warmup, Form
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase


@tagged('out_of_office')
class TestOutOfOffice(TestHrHolidaysBase):

    def setUp(self):
        super().setUp()
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'validity_start': False,
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
            'out_of_office_message': 'contact tde in case of problems',
            'number_of_days': 4,
        })
        leave.action_approve()
        self.assertEqual(self.employee_hruser.user_id.im_status, 'leave_offline', 'user should be out (leave_offline)')
        self.assertEqual(self.employee_hruser.user_id.partner_id.im_status, 'leave_offline', 'user should be out (leave_offline)')

        partner = self.employee_hruser.user_id.partner_id
        partner2 = self.user_employee.partner_id

        channel = self.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_channel_noautofollow': True,
        }).create({
            'channel_partner_ids': [(4, partner.id), (4, partner2.id)],
            'public': 'private',
            'channel_type': 'chat',
            'email_send': False,
            'name': 'test'
        })
        infos = channel.with_user(self.user_employee).channel_info()
        self.assertEqual(infos[0]['direct_partner'][0]['out_of_office_date_end'], leave_date_end)
        self.assertEqual(infos[0]['direct_partner'][0]['out_of_office_message'], 'contact tde in case of problems')

    def test_leave_ooo_use_default(self):
        """ Out of office message from Preferences should be used as default value """
        self.user_hruser.out_of_office_message = 'contact xdo in case of problems'

        leave_form = Form(self.env['hr.leave'].with_user(self.user_hruser), view='hr_holidays.hr_leave_view_form')
        leave_form.date_from = datetime.today() - relativedelta(days=1)
        leave_form.date_to = datetime.today()
        leave_form.holiday_status_id = self.leave_type
        leave = leave_form.save()
        self.assertEqual(leave.out_of_office_message, 'contact xdo in case of problems')

    def test_leave_ooo_overwrite_default(self):
        """ Out of office message default value should be overwrittable """
        self.user_hruser.out_of_office_message = 'contact xdo in case of problems'

        leave_form = Form(self.env['hr.leave'].with_user(self.user_hruser), view='hr_holidays.hr_leave_view_form')
        leave_form.date_from = datetime.today() - relativedelta(days=1)
        leave_form.date_to = datetime.today()
        leave_form.holiday_status_id = self.leave_type
        leave_form.out_of_office_message = 'contact tde in case of problems'
        leave = leave_form.save()
        self.assertEqual(leave.out_of_office_message, 'contact tde in case of problems')


@tagged('out_of_office')
class TestOutOfOfficePerformance(TestHrHolidaysBase):

    def setUp(self):
        super(TestOutOfOfficePerformance, self).setUp()
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'validity_start': False,
        })
        self.leave_date_end = (datetime.today() + relativedelta(days=3))
        self.leave = self.env['hr.leave'].create({
            'name': 'Christmas',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.leave_type.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'out_of_office_message': 'contact tde in case of problems',
            'number_of_days': 4,
        })

        self.hr_user = self.employee_hruser.user_id
        self.hr_partner = self.employee_hruser.user_id.partner_id
        self.employer_partner = self.user_employee.partner_id
        self.hr_user.flush()

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_offline(self):
        with self.assertQueryCount(__system__=2, demo=2):
            self.assertEqual(self.employer_partner.im_status, 'offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_user_leave_offline(self):
        with self.assertQueryCount(__system__=2, demo=2):
            self.assertEqual(self.hr_user.im_status, 'leave_offline')

    @users('__system__', 'demo')
    @warmup
    def test_leave_im_status_performance_partner_leave_offline(self):
        with self.assertQueryCount(__system__=2, demo=2):
            self.assertEqual(self.hr_partner.im_status, 'leave_offline')
