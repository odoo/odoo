# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.event.tests.common import EventCase
from odoo.exceptions import ValidationError
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestEventFlow(EventCase):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_auto_confirm(self):
        """ Basic event management with auto confirmation """
        # EventUser creates a new event: ok
        test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
            'name': 'TestEvent',
            'auto_confirm': True,
            'date_begin': datetime.datetime.now() + relativedelta(days=-1),
            'date_end': datetime.datetime.now() + relativedelta(days=1),
            'seats_max': 2,
            'seats_limited': True,
        })
        self.assertTrue(test_event.auto_confirm)

        # EventUser create registrations for this event
        test_reg1 = self.env['event.registration'].with_user(self.user_eventuser).create({
            'name': 'TestReg1',
            'event_id': test_event.id,
        })
        self.assertEqual(test_reg1.state, 'open', 'Event: auto_confirmation of registration failed')
        self.assertEqual(test_event.seats_reserved, 1, 'Event: wrong number of reserved seats after confirmed registration')
        test_reg2 = self.env['event.registration'].with_user(self.user_eventuser).create({
            'name': 'TestReg2',
            'event_id': test_event.id,
        })
        self.assertEqual(test_reg2.state, 'open', 'Event: auto_confirmation of registration failed')
        self.assertEqual(test_event.seats_reserved, 2, 'Event: wrong number of reserved seats after confirmed registration')

        # EventUser create registrations for this event: too much registrations
        with self.assertRaises(ValidationError):
            self.env['event.registration'].with_user(self.user_eventuser).create({
                'name': 'TestReg3',
                'event_id': test_event.id,
            })

        # EventUser validates registrations
        test_reg1.action_set_done()
        self.assertEqual(test_reg1.state, 'done', 'Event: wrong state of attended registration')
        self.assertEqual(test_event.seats_used, 1, 'Event: incorrect number of attendees after closing registration')
        test_reg2.action_set_done()
        self.assertEqual(test_reg1.state, 'done', 'Event: wrong state of attended registration')
        self.assertEqual(test_event.seats_used, 2, 'Event: incorrect number of attendees after closing registration')

    @users('user_eventmanager')
    def test_event_default_datetime(self):
        """ Check that the default date_begin and date_end are correctly set """

        # Should apply default datetimes
        with freeze_time(self.reference_now):
            default_event = self.env['event.event'].create({
                'name': 'Test Default Event',
            })
        self.assertEqual(default_event.date_begin, datetime.datetime.strptime('2022-09-05 15:30:00', '%Y-%m-%d %H:%M:%S'))
        self.assertEqual(default_event.date_end, datetime.datetime.strptime('2022-09-06 15:30:00', '%Y-%m-%d %H:%M:%S'))

        specific_datetimes = {
            'date_begin': self.reference_now + relativedelta(days=1),
            'date_end': self.reference_now + relativedelta(days=3),
        }

        # Should not apply default datetimes if values are set manually
        with freeze_time(self.reference_now):
            event = self.env['event.event'].create({
                'name': 'Test Event',
                **specific_datetimes,
            })
        self.assertEqual(event.date_begin, specific_datetimes['date_begin'])
        self.assertEqual(event.date_end, specific_datetimes['date_end'])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_flow(self):
        """ Advanced event flow: no auto confirmation, manage minimum / maximum
        seats, ... """
        # EventUser creates a new event: ok
        test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
            'name': 'TestEvent',
            'date_begin': datetime.datetime.now() + relativedelta(days=-1),
            'date_end': datetime.datetime.now() + relativedelta(days=1),
            'seats_limited': True,
            'seats_max': 10,
        })
        self.assertFalse(test_event.auto_confirm)

        # EventUser create registrations for this event -> no auto confirmation
        test_reg1 = self.env['event.registration'].with_user(self.user_eventuser).create({
            'name': 'TestReg1',
            'event_id': test_event.id,
        })
        self.assertEqual(
            test_reg1.state, 'draft',
            'Event: new registration should not be confirmed with auto_confirmation parameter being False')
