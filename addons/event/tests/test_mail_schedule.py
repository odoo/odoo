# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.event.tests.common import TestEventCommon
from openerp.tools import mute_logger

class TestMailSchedule(TestEventCommon):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_event_mail_schedule(self):
        """creating a mail schedule with a event"""
        # Eventmanagetr creates a new event: ok
        test_event = self.Event.sudo(self.user_eventmanager).create({
            'name': 'TestEventMail',
            'date_begin': datetime.datetime.now() + relativedelta(days=-1),
            'date_end': datetime.datetime.now() + relativedelta(days=1),
            'seats_max': 10,
        })
        # check Event must have two mail schedules
        self.assertEqual(len(test_event.event_mail_id), 3, 'event: set_mail_schedule: At least two Mail Scheduler has been set.')
        # EventUser create registrations for this event
        test_reg1 = self.Registration.sudo(self.user_eventuser).create({
            'name': 'TestReg1',
            'event_id': test_event.id,
        })
        #check user must be subscribed
        self.assertEqual(len(test_event.registration_ids), 1, 'event: user_subscribe: one user must be Subscribed')
        # run Scheduler
        self.EventMail.action_event_mail_scheduler()
        # check Mail Sent or not
        self.assertEqual(test_event.registration_ids.scheduler_mail_sent, True, 'Event: registration Mail should be sent')
