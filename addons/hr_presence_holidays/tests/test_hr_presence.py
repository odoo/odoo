# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from contextlib import contextmanager

from odoo import fields

from odoo.tests import common
from odoo.addons.test_mail.tests.common import mail_new_test_user


class testHrPresence(common.TransactionCase):

    @contextmanager
    def _patch_now(self, datetime_str):
        datetime_now_old = getattr(fields.Datetime, 'now')
        datetime_today_old = getattr(fields.Datetime, 'today')

        def new_now():
            return fields.Datetime.from_string(datetime_str)

        def new_today():
            return fields.Datetime.from_string(datetime_str).replace(hour=0, minute=0, second=0)

        try:
            setattr(fields.Datetime, 'now', new_now)
            setattr(fields.Datetime, 'today', new_today)

            yield
        finally:
            # back
            setattr(fields.Datetime, 'now', datetime_now_old)
            setattr(fields.Datetime, 'today', datetime_today_old)

    def setUp(self):
        super().setUp()
        self.user = mail_new_test_user(self.env, login='marc', groups='base.group_user')
        self.employee_without_user = self.env['hr.employee'].create({
            'name': 'Marc',
        })
        self.employee_with_user = self.env['hr.employee'].create({
            'name': 'Marc',
            'user_id': self.user.id,
        })

        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'validity_start': False,
        })

    def test_00_presence(self):
        """ Test presence during working hours """
        with self._patch_now('2019-06-27 09:00:00'):
            self.assertEqual(self.employee_with_user.hr_presence_state, 'to_define', 'Must be checked, as employee is not online')
            self.assertEqual(self.employee_without_user.hr_presence_state, 'to_define', 'Must be checked, as employee is in working hours.')
            self.user.im_status = 'online'
            self.assertEqual(self.employee_with_user.hr_presence_state, 'present', 'Employee is online.')

    def test_01_presence(self):
        """ Test presence outside working hours """
        with self._patch_now('2019-06-27 02:00:00'):
            self.assertEqual(self.employee_with_user.hr_presence_state, 'absent', 'Employee is not online but it is not his working hours.')
            self.assertEqual(self.employee_without_user.hr_presence_state, 'absent', 'Employee is outside his working hours.')
            self.user.im_status = 'online'
            self.assertEqual(self.employee_with_user.hr_presence_state, 'present', 'Employee is online.')

    def test_02_presence(self):
        """ Test presence during holidays """
        with self._patch_now('2019-06-27 09:00:00'):
            leave = self.env['hr.leave'].create({
                'name': 'holiday',
                'employee_id': self.employee_with_user.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': fields.Datetime.today(),
                'date_to': fields.Datetime.today() + relativedelta(days=1),
                'number_of_days': 1,
            })
            leave.action_approve()
            self.assertEqual(self.employee_with_user.hr_presence_state, 'absent', 'Employee is on holidays.')
            self.user.im_status = 'online'
            self.assertEqual(self.employee_with_user.hr_presence_state, 'absent', 'Employee is absent as he is in holiday (even he is online on database).')

    def test_03_presence(self):
        """ Test presence: First manually set present, then employee take leave """
        with self._patch_now('2019-06-27 09:00:00'):
            self.env['hr.employee']._check_presence()
            self.assertEqual(self.employee_with_user.hr_presence_state, 'to_define', 'Must be checked, as employee is not online')
            self.employee_with_user.sudo().action_set_present()
            self.employee_with_user._compute_presence_state()
            self.assertEqual(self.employee_with_user.hr_presence_state, 'present', 'This employee has been set manually present')

            leave = self.env['hr.leave'].create({
                'name': 'holiday',
                'employee_id': self.employee_with_user.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': fields.Datetime.today(),
                'date_to': fields.Datetime.today() + relativedelta(days=1),
                'number_of_days': 1,
            })
            leave.action_approve()
            self.assertEqual(self.employee_with_user.hr_presence_state, 'absent', 'Employee is on holidays.')
            self.user.im_status = 'online'
            self.assertEqual(self.employee_with_user.hr_presence_state, 'absent', 'Employee is absent as he is in holiday (even he is online on database).')
