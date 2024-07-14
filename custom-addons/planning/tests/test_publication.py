# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime

from .common import TestCommonPlanning


class TestPlanningPublishing(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super(TestPlanningPublishing, cls).setUpClass()

        cls.setUpEmployees()

        # employee without work email
        cls.employee_dirk_no_mail = cls.env['hr.employee'].create({
            'user_id': False,
            'name': 'Dirk',
            'work_email': False,
            'tz': 'UTC'
        })
        cls.resource_dirk = cls.employee_dirk_no_mail.resource_id

        values = {
            'resource_id': cls.resource_joseph.id,
            'allocated_hours': 8,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0)
        }
        cls.shift = cls.env['planning.slot'].create(values)

    def test_planning_publication(self):
        self.shift.write({
            'allocated_hours': 10
        })

        Mails = self.env['mail.mail'].sudo()
        before_mails = Mails.search([])

        self.shift.action_send()
        self.assertEqual(self.shift.state, 'published', 'planning is published when we call its action_send')

        shift_mails = set(Mails.search([])) ^ set(before_mails)
        self.assertEqual(len(shift_mails), 1, 'only one mail is created when publishing planning')

    def test_sending_planning_do_not_create_mail_if_employee_has_no_email(self):
        self.shift.write({'resource_id': self.resource_dirk.id})

        self.assertFalse(self.employee_dirk_no_mail.work_email)  # if no work_email

        Mails = self.env['mail.mail'].sudo()
        before_mails = Mails.search([])

        self.shift.action_send()
        shift_mails = set(Mails.search([])) ^ set(before_mails)
        self.assertEqual(len(shift_mails), 0, 'no mail should be sent when the employee has no work email')
