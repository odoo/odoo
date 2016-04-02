# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from openerp import fields, tools
from openerp.addons.event.tests.common import TestEventCommon
from openerp.tools import mute_logger


class TestMailSchedule(TestEventCommon):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_event_mail_schedule(self):
        """ Test mail scheduling for events """
        self.env['ir.values'].set_default('event.config.settings', 'auto_confirmation', True)
        now = fields.datetime.now()
        event_date_begin = now + relativedelta(days=1)
        event_date_end = now + relativedelta(days=3)

        test_event = self.Event.sudo(self.user_eventmanager).create({
            'name': 'TestEventMail',
            'date_begin': event_date_begin,
            'date_end': event_date_end,
            'seats_max': 10,
            'event_mail_ids': [
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_subscription')}),
                (0, 0, {  # 2 days before event
                    'interval_nbr': 2,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_reminder')}),
            ]
        })

        # create some registrations
        self.Registration.sudo(self.user_eventuser).create({
            'event_id': test_event.id,
            'name': 'Reg0',
            'email': 'reg0@example.com',
        })
        self.Registration.sudo(self.user_eventuser).create({
            'event_id': test_event.id,
            'name': 'Reg1',
            'email': 'reg1@example.com',
        })

        # check subscription scheduler
        schedulers = self.EventMail.search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub')])
        self.assertEqual(len(schedulers), 1, 'event: wrong scheduler creation')
        self.assertEqual(schedulers[0].scheduled_date, test_event.create_date, 'event: incorrect scheduled date for checking controller')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(schedulers[0].mail_registration_ids), 2, 'event: incorrect number of mail scheduled date')

        mails = self.env['mail.mail'].search([('subject', 'ilike', 'subscription'), ('date', '>=', datetime.datetime.strftime(now, tools.DEFAULT_SERVER_DATETIME_FORMAT))], order='date DESC', limit=3)
        self.assertEqual(len(mails), 2, 'event: wrong number of subscription mail sent')

        for registration in schedulers[0].mail_registration_ids:
            self.assertTrue(registration.mail_sent, 'event: wrongly confirmed mailing on subscription')

        # check before event scheduler
        schedulers = self.EventMail.search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(schedulers), 1, 'event: wrong scheduler creation')
        self.assertEqual(schedulers[0].scheduled_date, datetime.datetime.strftime(event_date_begin + relativedelta(days=-2), tools.DEFAULT_SERVER_DATETIME_FORMAT), 'event: incorrect scheduled date')

        # execute event reminder scheduler explicitly
        schedulers[0].execute()

        self.assertTrue(schedulers[0].mail_sent, 'event: reminder scheduler should have sent an email')
        self.assertTrue(schedulers[0].done, 'event: reminder scheduler should be done')

        mails = self.env['mail.mail'].search([('subject', 'ilike', 'reminder'), ('date', '>=', datetime.datetime.strftime(now, tools.DEFAULT_SERVER_DATETIME_FORMAT))], order='date DESC', limit=3)
        self.assertEqual(len(mails), 2, 'event: wrong number of reminders in outgoing mail queue')


