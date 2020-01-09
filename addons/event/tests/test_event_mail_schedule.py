# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.event.tests.common import TestEventCommon
from odoo.tools import mute_logger


class TestMailSchedule(TestEventCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailSchedule, cls).setUpClass()
        cls.now = fields.Datetime.now()
        cls.event_date_begin = cls.now + relativedelta(days=1)
        cls.event_date_end = cls.now + relativedelta(days=3)
        cls.test_event = cls.env['event.event'].with_user(cls.user_eventmanager).create({
            'name': 'TestEventMail',
            'auto_confirm': True,
            'date_begin': cls.event_date_begin,
            'date_end': cls.event_date_end,
            'event_mail_ids': [
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_id': cls.env['ir.model.data'].xmlid_to_res_id('event.event_subscription')}),
                (0, 0, {  # 1 days before event
                    'interval_nbr': 1,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'template_id': cls.env['ir.model.data'].xmlid_to_res_id('event.event_reminder')}),
            ]
        })

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_mail_schedule(self):
        """ Test mail scheduling for events """
        # create some registrations
        self.env['event.registration'].with_user(self.user_eventuser).create({
            'event_id': self.test_event.id,
            'name': 'Reg0',
            'email': 'reg0@example.com',
        })
        self.env['event.registration'].with_user(self.user_eventuser).create({
            'event_id': self.test_event.id,
            'name': 'Reg1',
            'email': 'reg1@example.com',
        })

        # check subscription scheduler
        schedulers = self.env['event.mail'].search([('event_id', '=', self.test_event.id), ('interval_type', '=', 'after_sub')])
        self.assertEqual(len(schedulers), 1, 'event: wrong scheduler creation')
        self.assertEqual(schedulers[0].scheduled_date, self.test_event.create_date, 'event: incorrect scheduled date for checking controller')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(schedulers[0].mail_registration_ids), 2, 'event: incorrect number of mail scheduled date')

        mails = self.env['mail.mail'].sudo().search([('subject', 'ilike', 'registration'), ('date', '>=', self.now)], order='date DESC', limit=3)
        self.assertEqual(len(mails), 2, 'event: wrong number of registration mail sent')

        for registration in schedulers[0].mail_registration_ids:
            self.assertTrue(registration.mail_sent, 'event: wrongly confirmed mailing on registration')

        # check before event scheduler
        schedulers = self.env['event.mail'].search([('event_id', '=', self.test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(schedulers), 1, 'event: wrong scheduler creation')
        self.assertEqual(schedulers[0].scheduled_date, self.event_date_begin + relativedelta(days=-1), 'event: incorrect scheduled date')

        # execute event reminder scheduler explicitly
        schedulers[0].execute()

        self.assertTrue(schedulers[0].mail_sent, 'event: reminder scheduler should have sent an email')
        self.assertTrue(schedulers[0].done, 'event: reminder scheduler should be done')

        mails = self.env['mail.mail'].sudo().search([('subject', 'ilike', 'TestEventMail'), ('date', '>=', self.now)], order='date DESC', limit=3)
        self.assertEqual(len(mails), 3, 'event: wrong number of reminders in outgoing mail queue')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_mail_schedule_trigger_stage(self):
        """Test mail scheduling for events."""
        stage_trigger = self.env['event.stage'].search([('name', '=', 'Announced')])

        test_event_mail = self.env['event.mail'].with_user(self.user_eventmanager).create({
            'event_id': self.test_event.id,
            'interval_nbr': 3,
            'interval_unit': 'days',
            'interval_type': 'stage_update',
            'trigger_stage_id': stage_trigger.id,
        })

        self.assertEqual(test_event_mail.trigger_stage_date, False)
        self.test_event.stage_id = self.env['event.stage'].search([('name', '=', 'Booked')])
        self.assertEqual(test_event_mail.trigger_stage_date, False)
        self.test_event.stage_id = stage_trigger
        self.assertAlmostEqual(test_event_mail.trigger_stage_date, self.now, delta=datetime.timedelta(minutes=1))
        self.assertAlmostEqual(test_event_mail.scheduled_date, self.now + datetime.timedelta(days=3), delta=datetime.timedelta(minutes=1))

        # changing the stage should not affect the `trigger_stage_date` if it's already set
        test_event_mail.trigger_stage_date = self.now - relativedelta(days=1)
        self.test_event.stage_id = self.env['event.stage'].search([('name', '=', 'Booked')])
        self.test_event.stage_id = stage_trigger
        self.assertAlmostEqual(test_event_mail.trigger_stage_date, self.now - relativedelta(days=1), delta=relativedelta(minutes=1))
