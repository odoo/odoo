# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta
from odoo.tests.common import new_test_user
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleEvent, GoogleCalendarService
from odoo import Command, tools
from unittest.mock import patch

class TestSyncGoogle2Odoo(TestSyncGoogle):

    def setUp(self):
        super().setUp()
        self.public_partner = self.env['res.partner'].create({
            'name': 'Public Contact',
            'email': 'public_email@example.com',
            'type': 'contact',
        })
        self.env.ref('base.partner_admin').write({
            'name': 'Mitchell Admin',
            'email': 'admin@yourcompany.example.com',
        })
        self.private_partner = self.env['res.partner'].create({
            'name': 'Private Contact',
            'email': 'private_email@example.com',
            'type': 'private',
        })

    def generate_recurring_event(self, mock_dt, **values):
        """ Function Used to return a recurrence created at fake time of 'mock_dt'. """
        rrule = values.pop('rrule', None)
        google_id = values.pop('google_id', None)
        with self.mock_datetime_and_now(mock_dt):
            base_event = self.env['calendar.event'].with_user(self.organizer_user).create({
                'name': 'coucou',
                'need_sync': False,
                **values
            })
            recurrence = self.env['calendar.recurrence'].with_user(self.organizer_user).create({
                'google_id': google_id,
                'rrule': rrule,
                'need_sync': False,
                'base_event_id': base_event.id,
            })
            recurrence._apply_recurrence()
        return recurrence

    def google_respond_to_recurrent_event_with_option_this_event(self, recurrence, event_index, response_status):
        """
        Function returns google api response simulating 'self.attendee_user' responding to the event number 'event_index' (0-indexed)
        in 'recurrence' with response of 'response_status' and option "This event"
        """
        update_time = (recurrence.write_date + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recurrence_google_values = recurrence._google_values()
        recurrence_google_values['updated'] = update_time
        updated_event_google_values = recurrence.calendar_event_ids.sorted('start')[event_index]._google_values()
        updated_event_google_values['updated'] = update_time
        updated_event_google_values['attendees'] = [
            {"email": self.organizer_user.partner_id.email, "responseStatus": "accepted"},
            {"email": self.attendee_user.partner_id.email, "responseStatus": response_status},
        ]
        return [
            recurrence_google_values,
            updated_event_google_values,
        ]

    def google_respond_to_recurrent_event_with_option_all_events(self, recurrence, response_status):
        """
        Function returns google api response simulating 'self.attendee_user' responding to 'recurrence'
        with response of 'response_status' and option "All events"
        """
        update_time = (recurrence.write_date + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recurrence_google_values = recurrence._google_values()
        recurrence_google_values['updated'] = update_time
        recurrence_google_values['attendees'] = [
            {"email": self.organizer_user.partner_id.email, "responseStatus": "accepted"},
            {"email": self.attendee_user.partner_id.email, "responseStatus": response_status},
        ]
        return [recurrence_google_values]

    def google_respond_to_recurrent_event_with_option_following_events(self, recurrence, event_index, response_status, rrule1, rrule2):
        """
        Function returns google api response simulating 'self.attendee_user' responding to the event number 'event_index' (0-indexed)
        in 'recurrence' with response of 'response_status' and option "This and following events".
        """
        update_time = (recurrence.write_date + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recurrence_google_values = recurrence._google_values()
        recurrence_google_values['updated'] = update_time
        updated_event_google_values = recurrence.calendar_event_ids.sorted('start')[event_index]._google_values()
        updated_event_google_values['updated'] = update_time
        updated_event_google_values['attendees'] = [
            {"email": self.organizer_user.partner_id.email, "responseStatus": "accepted"},
            {"email": self.attendee_user.partner_id.email, "responseStatus": response_status},
        ]
        updated_event_id = updated_event_google_values['id']
        updated_event_google_values['id'] = updated_event_id[:updated_event_id.index('_') + 1] + 'R' + updated_event_id[updated_event_id.index('_') + 1:]
        recurrence_google_values["recurrence"] = [rrule1]
        updated_event_google_values["recurrence"] = [rrule2]
        return [
            recurrence_google_values,
            updated_event_google_values,
        ]

    @property
    def now(self):
        return pytz.utc.localize(datetime.now()).isoformat()

    def sync(self, events):
        events.clear_type_ambiguity(self.env)
        google_recurrence = events.filter(GoogleEvent.is_recurrence)
        self.env['calendar.recurrence']._sync_google2odoo(google_recurrence)
        self.env['calendar.event']._sync_google2odoo(events - google_recurrence)

    @patch_api
    def test_new_google_event(self):
        description = '<script>alert("boom")</script><p style="white-space: pre"><h1>HELLO</h1></p><ul><li>item 1</li><li>item 2</li></ul>'
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': description,
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            },],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(event, "It should have created an event")
        self.assertEqual(event.name, values.get('summary'))
        self.assertFalse(event.allday)
        self.assertEqual(event.description, tools.html_sanitize(description))
        self.assertEqual(event.start, datetime(2020, 1, 13, 15, 55))
        self.assertEqual(event.stop, datetime(2020, 1, 13, 18, 55))
        admin_attendee = event.attendee_ids.filtered(lambda e: e.email == self.public_partner.email)
        self.assertEqual(self.public_partner.email, admin_attendee.email)
        self.assertEqual(self.public_partner.name, admin_attendee.partner_id.name)
        self.assertEqual(event.partner_ids, event.attendee_ids.partner_id)
        self.assertEqual('needsAction', admin_attendee.state)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_invalid_owner_property(self):
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'extendedProperties': {
                'shared':  {'%s_owner_id' % self.env.cr.dbname: "invalid owner id"}
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertEqual(event.user_id, self.env.user)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_valid_owner_property(self):
        user = new_test_user(self.env, login='calendar-user')
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'extendedProperties': {
                'shared':  {'%s_owner_id' % self.env.cr.dbname: str(user.id)}
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertEqual(event.user_id, user)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_cancelled(self):
        """ Cancel event when the current user is the organizer """
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'google_id': google_id,
            'user_id': self.env.user.id,
            'need_sync': False,
            'partner_ids': [(6, 0, self.env.user.partner_id.ids)]  # current user is attendee
        })
        gevent = GoogleEvent([{
            'id': google_id,
            'status': 'cancelled',
        }])
        self.sync(gevent)
        self.assertFalse(event.exists())
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_attendee_cancelled(self):
        """ Cancel event when the current user is not the organizer """
        user = new_test_user(self.env, login='calendar-user')
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': date(2020, 1, 5),
            'stop': date(2020, 1, 6),
            'allday': True,
            'google_id': google_id,
            'need_sync': False,
            'user_id': False,  # Not the current user
            'partner_ids': [Command.set(user.partner_id.ids)],
        })
        gevent = GoogleEvent([{
            'id': google_id,
            'status': 'cancelled',
        }])
        user_attendee = event.attendee_ids
        self.assertEqual(user_attendee.state, 'needsAction')
        # We have to call sync with the attendee user
        gevent.clear_type_ambiguity(self.env)
        self.env['calendar.event'].with_user(user)._sync_google2odoo(gevent)
        self.assertTrue(event.active)
        user_attendee = event.attendee_ids
        self.assertTrue(user_attendee)
        self.assertEqual(user_attendee.state, 'declined')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_cancelled_with_portal_attendee(self):
        """Cancel an event with a portal attendee.

        This test exercises a bug that only happened under these circumstances:
        - One portal user was invited to more than one event.
        - At least one of them was going to be notified in the future.
        - Google cancelled the first of those.
        """
        portal_user = new_test_user(self.env, login='portal-user', groups='base.group_portal')
        notif30min = self.ref("calendar.alarm_notif_2")
        # Cannot use freezegun because there are direct calls to now() from SQL
        now = datetime.now()
        one = self.env['calendar.event'].create({
            'name': 'test',
            'start': now + timedelta(hours=1),
            'stop': now + timedelta(hours=2),
            'google_id': 'one',
            'user_id': self.env.user.id,
            'need_sync': False,
            'alarm_ids': [(6, 0, [notif30min])],
            'partner_ids': [(6, 0, (self.env.user | portal_user).partner_id.ids)]
        })
        two = one.copy({
            'google_id': 'two',
            'start': now + timedelta(hours=2),
            'stop': now + timedelta(hours=3),
        })
        gevent = GoogleEvent([
            {'id': 'one', 'status': 'cancelled'},
        ])
        self.sync(gevent)
        self.assertFalse(one.exists())
        self.assertTrue(two.exists())

    @patch_api
    def test_private_extended_properties(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'allday': True,
            'google_id': google_id,
            'need_sync': False,
            'user_id': False,  # Not the current user
            'partner_ids': [(6, 0, self.env.user.partner_id.ids)]  # current user is attendee
        })
        user_attendee = event.attendee_ids
        self.assertTrue(user_attendee)
        self.assertEqual(user_attendee.state, 'accepted')
        user_attendee.do_decline()
        # To avoid 403 errors, we send a limited dictionnary when we don't have write access.
        # guestsCanModify property is not properly handled yet
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'summary': 'coucou',
            'start': {'date': str(event.start_date), 'dateTime': None},
            'end': {'date': str(event.stop_date + relativedelta(days=1)), 'dateTime': None},
            'attendees': [{'email': 'odoobot@example.com', 'responseStatus': 'declined'}],
            'extendedProperties': {'private': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'reminders': {'overrides': [], 'useDefault': False},
        })

    @patch_api
    def test_attendee_removed(self):
        user = new_test_user(self.env, login='calendar-user')
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].with_user(user).create({
            'name': 'coucou',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'google_id': google_id,
            'user_id': False,  # user is not owner
            'need_sync': False,
            'partner_ids': [(6, 0, user.partner_id.ids)],  # but user is attendee
        })
        gevent = GoogleEvent([{
            'id': google_id,
            'description': 'Small mini desc',
            "updated": self.now,
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [],  # <= attendee removed in Google
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }])
        self.assertEqual(event.partner_ids, user.partner_id)
        self.assertEqual(event.attendee_ids.partner_id, user.partner_id)
        self.sync(gevent)
        # User attendee removed but gevent owner might be added after synch.
        self.assertNotEqual(event.attendee_ids.partner_id, user.partner_id)
        self.assertNotEqual(event.partner_ids, user.partner_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_attendee_removed_multiple(self):

        user = new_test_user(self.env, login='calendar-user')
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'allday': True,
            'start': datetime(2020, 1, 6),
            'stop': datetime(2020, 1, 6),
            'user_id': False,  # user is not owner
            'need_sync': False,
            'partner_ids': [(6, 0, user.partner_id.ids)],  # but user is attendee
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()

        gevent = GoogleEvent([{
            'id': google_id,
            "updated": self.now,
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'coucou',
            'visibility': 'public',
            'attendees': [],  # <= attendee removed in Google
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
        }])
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(events.partner_ids, user.partner_id)
        self.assertEqual(events.attendee_ids.partner_id, user.partner_id)
        self.sync(gevent)
        # User attendee removed but gevent owner might be added after synch.
        self.assertNotEqual(events.attendee_ids.partner_id, user.partner_id)
        self.assertNotEqual(events.partner_ids, user.partner_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        values = {
            'id': recurrence_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
            'transparency': 'opaque',
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(recurrence, "it should have created a recurrence")
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertTrue(all(events.mapped('recurrency')))
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 13))
        self.assertEqual(events[2].start_date, date(2020, 1, 20))
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 13))
        self.assertEqual(events[2].start_date, date(2020, 1, 20))
        self.assertEqual(events[0].google_id, '%s_20200106' % recurrence_id)
        self.assertEqual(events[1].google_id, '%s_20200113' % recurrence_id)
        self.assertEqual(events[2].google_id, '%s_20200120' % recurrence_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_datetime(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        values = {
            'id': recurrence_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'dateTime': '2020-01-06T18:00:00+01:00'},
            'end': {'dateTime': '2020-01-06T19:00:00+01:00'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(recurrence, "it should have created a recurrence")
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertTrue(all(events.mapped('recurrency')))
        self.assertEqual(events[0].start, datetime(2020, 1, 6, 17, 0))
        self.assertEqual(events[1].start, datetime(2020, 1, 13, 17, 0))
        self.assertEqual(events[2].start, datetime(2020, 1, 20, 17, 0))
        self.assertEqual(events[0].google_id, '%s_20200106T170000Z' % recurrence_id)
        self.assertEqual(events[1].google_id, '%s_20200113T170000Z' % recurrence_id)
        self.assertEqual(events[2].google_id, '%s_20200120T170000Z' % recurrence_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_exdate(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        events = GoogleEvent([{
            'id': recurrence_id,
            'summary': 'Pricing new update',
            'organizer': {'email': self.env.user.email, 'self': True},
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
        }, {   # Third event has been deleted
            'id': '%s_20200113' % recurrence_id,
            'originalStartTime': {'dateTime': '2020-01-13'},
            'recurringEventId': 'oj44nep1ldf8a3ll02uip0c9pk',
            'reminders': {'useDefault': True},
            'status': 'cancelled',
        }])
        self.sync(events)
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', recurrence_id)])
        self.assertTrue(recurrence, "it should have created a recurrence")
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2, "it should have created a recurrence with 2 events")
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 20))
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_first_exdate(self):
        recurrence_id = "4c0de517evkk3ra294lmut57vm"
        events = GoogleEvent([{
            "id": recurrence_id,
            "updated": "2020-01-13T16:17:03.806Z",
            "summary": "r rul",
            "start": {"date": "2020-01-6"},
            'organizer': {'email': self.env.user.email, 'self': True},
            "end": {"date": "2020-01-7"},
            'reminders': {'useDefault': True},
            "recurrence": ["RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO"],
        }, {
            "id": "%s_20200106" % recurrence_id,
            "status": "cancelled",
            "recurringEventId": "4c0de517evkk3ra294lmut57vm",
            'reminders': {'useDefault': True},
            "originalStartTime": {
                "date": "2020-01-06"
            }
        }])
        self.sync(events)
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', recurrence_id)])
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2, "it should have created a recurrence with 2 events")
        self.assertEqual(events[0].start_date, date(2020, 1, 13))
        self.assertEqual(events[1].start_date, date(2020, 1, 20))
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrencde_first_updated(self):
        recurrence_id = "4c0de517evkk3ra294lmut57vm"
        events = GoogleEvent([{
            'id': recurrence_id,
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=WE'],
            'start': {'date': '2020-01-01'},
            'end': {'date': '2020-01-02'},
            'status': 'confirmed',
            'summary': 'rrule',
            'reminders': {'useDefault': True},
            'updated': self.now
        }, {
            'summary': 'edited',  # Name changed
            'id': '%s_20200101' % recurrence_id,
            'originalStartTime': {'date': '2020-01-01'},
            'recurringEventId': recurrence_id,
            'start': {'date': '2020-01-01'},
            'end': {'date': '2020-01-02'},
            'reminders': {'useDefault': True},
            'updated': self.now,
        }])
        self.sync(events)
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', recurrence_id)])
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertEqual(events[0].name, 'edited')
        self.assertEqual(events[1].name, 'rrule')
        self.assertEqual(events[2].name, 'rrule')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_existing_recurrence_first_updated(self):
        recurrence_id = "4c0de517evkk3ra294lmut57vm"
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'allday': True,
            'start': datetime(2020, 1, 6),
            'stop': datetime(2020, 1, 6),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': recurrence_id,
            'rrule': 'FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
        })
        recurrence._apply_recurrence()
        values = [{
            'summary': 'edited',  # Name changed
            'id': '%s_20200106' % recurrence_id,
            'originalStartTime': {'date': '2020-01-06'},
            'recurringEventId': recurrence_id,
            'start': {'date': '2020-01-06'},
            'end': {'date': '2020-01-07'},
            'reminders': {'useDefault': True},
            'updated': self.now,
        }]
        self.env['calendar.event']._sync_google2odoo(GoogleEvent(values))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', recurrence_id)])
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertEqual(events[0].name, 'edited')
        self.assertEqual(events[1].name, 'coucou')
        self.assertEqual(events[2].name, 'coucou')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_outlier(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        events = GoogleEvent([{
            'id': recurrence_id,
            'summary': 'Pricing new update',
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
            'reminders': {'useDefault': True},
            'updated': self.now,
        },
        {  # Third event has been moved
            'id': '%s_20200113' % recurrence_id,
            'summary': 'Pricing new update',
            'start': {'date': '2020-01-18'},
            'end': {'date': '2020-01-19'},
            'originalStartTime': {'date': '2020-01-13'},
            'reminders': {'useDefault': True},
            'updated': self.now,
        }])
        self.sync(events)
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', recurrence_id)])
        self.assertTrue(recurrence, "it should have created a recurrence")
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 18), "It should not be in sync with the recurrence")
        self.assertEqual(events[2].start_date, date(2020, 1, 20))
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_moved(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'allday': True,
            'start': datetime(2020, 1, 6),
            'stop': datetime(2020, 1, 6),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        values = {
            'id': google_id,
            'summary': 'coucou',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE'],  # Now wednesday
            'start': {'date': '2020-01-08'},
            'end': {'date': '2020-01-09'},
            'reminders': {'useDefault': True},
            "attendees": [
                {
                    "email": "odoobot@example.com", "state": "accepted",
                },
            ],
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2)
        self.assertEqual(recurrence.rrule, 'RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=WE')
        self.assertEqual(events[0].start_date, date(2020, 1, 8))
        self.assertEqual(events[1].start_date, date(2020, 1, 15))
        self.assertEqual(events[0].google_id, '%s_20200108' % google_id)
        self.assertEqual(events[1].google_id, '%s_20200115' % google_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_name_updated(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'allday': True,
            'start': datetime(2020, 1, 6),
            'stop': datetime(2020, 1, 6),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()

        values = {
            'id': google_id,
            'summary': 'coucou again',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=MO'],
            'start': {'date': '2020-01-06'},
            'end': {'date': '2020-01-07'},
            'reminders': {'useDefault': True},
            "attendees": [
                {
                    "email": "odoobot@example.com", "state": "accepted",
                },
            ],
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2)
        self.assertEqual(recurrence.rrule, 'RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=MO')
        self.assertEqual(events.mapped('name'), ['coucou again', 'coucou again'])
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 13))
        self.assertEqual(events[0].google_id, '%s_20200106' % google_id)
        self.assertEqual(events[1].google_id, '%s_20200113' % google_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_write_with_outliers(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': datetime(2021, 2, 15, 8, 0, 0),
            'stop': datetime(2021, 2, 15, 10, 0, 0),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(events[0].google_id, '%s_20210215T080000Z' % google_id)
        self.assertEqual(events[1].google_id, '%s_20210222T080000Z' % google_id)
        self.assertEqual(events[2].google_id, '%s_20210301T080000Z' % google_id)
        # Modify start of one of the events.
        middle_event = recurrence.calendar_event_ids.filtered(lambda e: e.start == datetime(2021, 2, 22, 8, 0, 0))
        middle_event.write({
            'start': datetime(2021, 2, 22, 16, 0, 0),
            'need_sync': False,
        })

        values = {
            'id': google_id,
            'summary': 'coucou again',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=3;BYDAY=MO'],
            'start': {'dateTime': '2021-02-15T09:00:00+01:00'}, # 8:00 UTC
            'end': {'dateTime': '2021-02-15-T11:00:00+01:00'},
            'reminders': {'useDefault': True},
            "attendees": [
                {
                    "email": "odoobot@example.com", "state": "accepted",
                },
            ],
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3)
        self.assertEqual(recurrence.rrule, 'RRULE:FREQ=WEEKLY;COUNT=3;BYDAY=MO')
        self.assertEqual(events.mapped('name'), ['coucou again', 'coucou again', 'coucou again'])
        self.assertEqual(events[0].start, datetime(2021, 2, 15, 8, 0, 0))
        self.assertEqual(events[1].start, datetime(2021, 2, 22, 16, 0, 0))
        self.assertEqual(events[2].start, datetime(2021, 3, 1, 8, 0, 0))
        # the google_id of recurrent events should not be modified when events start is modified.
        # the original start date or datetime should always be present.
        self.assertEqual(events[0].google_id, '%s_20210215T080000Z' % google_id)
        self.assertEqual(events[1].google_id, '%s_20210222T080000Z' % google_id)
        self.assertEqual(events[2].google_id, '%s_20210301T080000Z' % google_id)
        self.assertGoogleAPINotCalled()


    @patch_api
    def test_recurrence_write_time_fields(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': datetime(2021, 2, 15, 8, 0, 0),
            'stop': datetime(2021, 2, 15, 10, 0, 0),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        # Google modifies the start/stop of the base event
        # When the start/stop or all day values are updated, the recurrence should reapplied.

        values = {
            'id': google_id,
            'summary': "It's me again",
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=MO'],
            'start': {'dateTime': '2021-02-15T12:00:00+01:00'},  # 11:00 UTC
            'end': {'dateTime': '2021-02-15-T15:00:00+01:00'},
            'reminders': {'useDefault': True},
            "attendees": [
                {
                    "email": "odoobot@example.com", "state": "accepted",
                },
            ],
            'updated': self.now,
        }

        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(events[0].start, datetime(2021, 2, 15, 11, 0, 0))
        self.assertEqual(events[1].start, datetime(2021, 2, 22, 11, 0, 0))
        self.assertEqual(events[2].start, datetime(2021, 3, 1, 11, 0, 0))
        self.assertEqual(events[3].start, datetime(2021, 3, 8, 11, 0, 0))
        # We ensure that our modifications are pushed
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_deleted(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': datetime(2021, 2, 15, 8, 0, 0),
            'stop': datetime(2021, 2, 15, 10, 0, 0),
            'need_sync': False,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        events = recurrence.calendar_event_ids
        values = {
            'id': google_id,
            'status': 'cancelled',
        }
        self.sync(GoogleEvent([values]))
        self.assertFalse(recurrence.exists(), "The recurrence should be deleted")
        self.assertFalse(events.exists(), "All events should be deleted")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_timezone(self):
        """ Ensure that the timezone of the base_event is saved on the recurrency
        Google save the TZ on the event and we save it on the recurrency.
        """
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        values = {
            'id': recurrence_id,
            'description': '',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Event with ',
            'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'dateTime': '2020-01-06T18:00:00+01:00', 'timeZone': 'Pacific/Auckland'},
            'end': {'dateTime': '2020-01-06T19:00:00+01:00', 'timeZone': 'Pacific/Auckland'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', values.get('id'))])
        self.assertEqual(recurrence.event_tz, 'Pacific/Auckland', "The Google event Timezone should be saved on the recurrency")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_no_duplicate(self):
        values = [
            {
                "attendees": [
                    {
                        "email": "myemail@exampl.com",
                        "responseStatus": "needsAction",
                        "self": True,
                    },
                    {"email": "jane.doe@example.com", "responseStatus": "needsAction"},
                    {
                        "email": "john.doe@example.com",
                        "organizer": True,
                        "responseStatus": "accepted",
                    },
                ],
                "created": "2023-02-20T11:45:07.000Z",
                "creator": {"email": "john.doe@example.com"},
                "end": {"dateTime": "2023-02-25T16:20:00+01:00", "timeZone": "Europe/Zurich"},
                "etag": '"4611038912699385"',
                "eventType": "default",
                "iCalUID": "9lxiofipomymx2yr1yt0hpep99@google.com",
                "id": "9lxiofipomymx2yr1yt0hpep99",
                "kind": "calendar#event",
                "organizer": {"email": "john.doe@example.com"},
                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=SA"],
                "reminders": {"useDefault": True},
                "sequence": 0,
                "start": {"dateTime": "2023-02-25T15:30:00+01:00", "timeZone": "Europe/Zurich"},
                "status": "confirmed",
                "summary": "Weekly test",
                "updated": "2023-02-20T11:45:08.547Z",
            },
            {
                "attendees": [
                    {
                        "email": "myemail@exampl.com",
                        "responseStatus": "needsAction",
                        "self": True,
                    },
                    {
                        "email": "jane.doe@example.com",
                        "organizer": True,
                        "responseStatus": "needsAction",
                    },
                    {"email": "john.doe@example.com", "responseStatus": "accepted"},
                ],
                "created": "2023-02-20T11:45:44.000Z",
                "creator": {"email": "john.doe@example.com"},
                "end": {"dateTime": "2023-02-26T15:20:00+01:00", "timeZone": "Europe/Zurich"},
                "etag": '"5534851880843722"',
                "eventType": "default",
                "iCalUID": "hhb5t0cffjkndvlg7i22f7byn1@google.com",
                "id": "hhb5t0cffjkndvlg7i22f7byn1",
                "kind": "calendar#event",
                "organizer": {"email": "jane.doe@example.com"},
                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=SU"],
                "reminders": {"useDefault": True},
                "sequence": 0,
                "start": {"dateTime": "2023-02-26T14:30:00+01:00", "timeZone": "Europe/Zurich"},
                "status": "confirmed",
                "summary": "Weekly test 2",
                "updated": "2023-02-20T11:48:00.634Z",
            },
        ]
        google_events = GoogleEvent(values)
        self.env['calendar.recurrence']._sync_google2odoo(google_events)
        no_duplicate_gevent = google_events.filter(lambda e: e.id == "9lxiofipomymx2yr1yt0hpep99")
        dt_start = datetime.fromisoformat(no_duplicate_gevent.start["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=0)
        dt_end = datetime.fromisoformat(no_duplicate_gevent.end["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=23)
        no_duplicate_event = self.env["calendar.event"].search(
            [
                ("name", "=", no_duplicate_gevent.summary),
                ("start", ">=", dt_start),
                ("stop", "<=", dt_end,)
            ]
        )
        self.assertEqual(len(no_duplicate_event), 1)

    @patch_api
    def test_recurrence_list_contains_more_items(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        values = {
            'id': recurrence_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'recurrence': ['EXDATE;TZID=Europe/Rome:20200113',
                           'RRULE;X-EVOLUTION-ENDDATE=20200120:FREQ=WEEKLY;COUNT=3;BYDAY=MO;X-RELATIVE=1'],
            'reminders': {'useDefault': True},
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(recurrence, "it should have created a recurrence")
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertTrue(all(events.mapped('recurrency')))
        self.assertEqual(events[0].start_date, date(2020, 1, 6))
        self.assertEqual(events[1].start_date, date(2020, 1, 13))
        self.assertEqual(events[2].start_date, date(2020, 1, 20))
        self.assertEqual(events[0].stop_date, date(2020, 1, 6))
        self.assertEqual(events[1].stop_date, date(2020, 1, 13))
        self.assertEqual(events[2].stop_date, date(2020, 1, 20))
        self.assertEqual(events[0].google_id, '%s_20200106' % recurrence_id)
        self.assertEqual(events[1].google_id, '%s_20200113' % recurrence_id)
        self.assertEqual(events[2].google_id, '%s_20200120' % recurrence_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_simple_event_into_recurrency(self):
        """ Synched single events should be converted in recurrency without problems"""
        google_id = 'aaaaaaaaaaaa'
        values = {
            'id': google_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }, ],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-06T18:00:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        # The event is transformed into a recurrency on google
        values = {
            'id': google_id,
            'description': '',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Event with ',
            'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'dateTime': '2020-01-06T18:00:00+01:00', 'timeZone': 'Europe/Brussels'},
            'end': {'dateTime': '2020-01-06T19:00:00+01:00', 'timeZone': 'Europe/Brussels'},
        }
        recurrence = self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertFalse(event.exists(), "The old event should not exits anymore")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_reduced(self):
        # This test is a bit special because it's testing 2 sync processes. The
        # bug it's protecting against is cross-contamination when event dicts
        # are mutated in different ways during the call to
        # `_sync_google_calendar()`. If you want to do a new test, this one is
        # probably not the best example.
        google_id = "oj44nep1ldf8a3ll02uip0c9aa"
        with self.mock_datetime_and_now("2024-06-07"):
            # We start with an event with 2 repetitions
            values = [
                # Recurrence from day 7 changes
                {
                    "id": google_id,
                    "summary": "coucou",
                    "recurrence": [
                        "RRULE:FREQ=WEEKLY;WKST=MO;UNTIL=20240620T215959Z;BYDAY=FR"
                    ],
                    "start": {"dateTime": "2024-06-07T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-07T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
                # Event details for day 7
                {
                    "id": "%s_20240607T080000Z" % google_id,
                    "summary": "coucou",
                    "start": {"dateTime": "2024-06-07T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-07T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "recurringEventId": google_id,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
                # Event details for day 14
                {
                    "id": "%s_20240614T080000Z" % google_id,
                    "summary": "coucou",
                    "start": {"dateTime": "2024-06-14T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-14T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "recurringEventId": google_id,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
            ]
            with patch.object(
                GoogleCalendarService,
                "get_events",
                return_value=(
                    GoogleEvent(values),
                    None,
                    [{"method": "popup", "minutes": 30}],
                ),
            ):
                self.attendee_user.sudo()._sync_google_calendar(self.google_service)
            events = self.env["calendar.event"].search(
                [("google_id", "like", google_id)]
            )
            self.assertEqual(len(events.exists()), 2)

        with self.mock_datetime_and_now("2024-06-10"):
            # From Google Calendar, they alter events from day 14 onwards and move
            # them 1h later. However, they regret and move them back 1h again.
            values = [
                # Recurrence from day 7 changes
                {
                    "id": google_id,
                    "summary": "coucou",
                    "recurrence": [
                        "RRULE:FREQ=WEEKLY;WKST=MO;UNTIL=20240613T215959Z;BYDAY=FR"
                    ],
                    "start": {"dateTime": "2024-06-07T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-07T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
                # Event details for day 7
                {
                    "id": "%s_20240607T080000Z" % google_id,
                    "summary": "coucou",
                    "start": {"dateTime": "2024-06-07T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-07T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "recurringEventId": google_id,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
                # Event details for day 14
                {
                    "id": "%s_20240614T080000Z" % google_id,
                    "summary": "coucou",
                    "start": {"dateTime": "2024-06-14T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-14T10:00:00+00:00"},
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "recurringEventId": "%s_R20240614T080000" % google_id,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
                # New recurrence that starts on day 14
                {
                    "id": "%s_R20240614T080000" % google_id,
                    "summary": "coucou",
                    "start": {"dateTime": "2024-06-14T08:00:00+00:00"},
                    "end": {"dateTime": "2024-06-14T10:00:00+00:00"},
                    "recurrence": [
                        "RRULE:FREQ=WEEKLY;WKST=MO;UNTIL=20240620T215959Z;BYDAY=FR"
                    ],
                    "reminders": {"useDefault": True},
                    "updated": self.now,
                    "attendees": [
                        {
                            "email": self.organizer_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                        {
                            "email": self.attendee_user.partner_id.email,
                            "responseStatus": "accepted",
                        },
                    ],
                },
            ]
            # Then, Odoo syncs
            with patch.object(
                GoogleCalendarService,
                "get_events",
                return_value=(
                    GoogleEvent(values),
                    None,
                    [{"method": "popup", "minutes": 30}],
                ),
            ):
                self.attendee_user.sudo()._sync_google_calendar(self.google_service)
            events = self.env["calendar.event"].search(
                [("google_id", "like", google_id)]
            )
            self.assertEqual(len(events.exists()), 2)

    @patch_api
    def test_new_google_notifications(self):
        """ Event from Google should not create notifications and trigger. It ruins the perfs on large databases """
        cron_id = self.env.ref('calendar.ir_cron_scheduler_alarm').id
        triggers_before = self.env['ir.cron.trigger'].search([('cron_id', '=', cron_id)])
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        start = datetime.today() + relativedelta(months=1, day=1, hours=1)
        end = datetime.today() + relativedelta(months=1, day=1, hours=2)
        updated = datetime.today() + relativedelta(minutes=1)
        values = {
            'id': google_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }, ],
            'reminders': {'overrides': [{"method": "email", "minutes": 10}], 'useDefault': False},
            'start': {
                'dateTime': pytz.utc.localize(start).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': pytz.utc.localize(end).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        triggers_after = self.env['ir.cron.trigger'].search([('cron_id', '=', cron_id)])
        new_triggers = triggers_after - triggers_before
        self.assertFalse(new_triggers, "The event should not be created with triggers.")

        # Event was created from Google and now it will be Updated from Google.
        # No further notifications should be created.
        values = {
            'id': google_id,
            'updated': pytz.utc.localize(updated).isoformat(),
            'description': 'New Super description',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing was not good, now it is correct',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }, ],
            'reminders': {'overrides': [{"method": "email", "minutes": 10}], 'useDefault': False},
            'start': {
                'dateTime': pytz.utc.localize(start).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': pytz.utc.localize(end).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        triggers_after = self.env['ir.cron.trigger'].search([('cron_id', '=', cron_id)])
        new_triggers = triggers_after - triggers_before
        self.assertFalse(new_triggers, "The event should not be created with triggers.")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_event_reminder_emails_with_google_id(self):
        """
        Odoo shouldn't send email reminders for synced events.
        Test that events synced to Google (with a `google_id`)
        are excluded from email alarm notifications.
        """
        now = datetime.now()
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        start = now - relativedelta(minutes=30)
        end = now + relativedelta(hours=2)
        alarm = self.env['calendar.alarm'].create({
            'name': 'Alarm',
            'alarm_type': 'email',
            'interval': 'minutes',
            'duration': 30,
        })
        values = {
            'id': google_id,
            "alarm_id": alarm.id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }],
            'start': {
                'dateTime': pytz.utc.localize(start).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
            'reminders': {'overrides': [{"method": "email", "minutes": 30}], 'useDefault': False},
            'end': {
                'dateTime': pytz.utc.localize(end).isoformat(),
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        events_by_alarm = self.env['calendar.alarm_manager']._get_events_by_alarm_to_notify('email')
        self.assertFalse(events_by_alarm, "Events with google_id should not trigger reminders")

    @patch_api
    def test_attendee_state(self):
        user = new_test_user(self.env, login='calendar-user')
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].with_user(user).create({
            'name': 'Event with me',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'google_id': google_id,
            'user_id': False,  # user is not owner
            'need_sync': False,
            'partner_ids': [(6, 0, user.partner_id.ids)],  # but user is attendee
        })
        self.assertEqual(event.attendee_ids.state, 'accepted')
        # The event is declined from Google
        values = {
            'id': google_id,
            'description': 'Changed my mind',
            "updated": self.now,
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': """I don't want to be with me anymore""",
            'visibility': 'public',
            'attendees': [{
                'displayName': 'calendar-user (base.group_user)',
                'email': 'c.c@example.com',
                'responseStatus': 'declined'
            }, ],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'date': None,
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'date': None,
                'timeZone': 'Europe/Brussels'
            },
            'transparency': 'opaque',
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        self.assertEqual(event.attendee_ids.state, 'declined')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_attendees_same_event_both_share(self):
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        other_user = new_test_user(self.env, login='calendar-user')
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'allday': True,
            'google_id': google_id,
            'need_sync': False,
            'user_id': other_user.id,  # Not the current user
            'partner_ids': [(6, 0, [self.env.user.partner_id.id, other_user.partner_id.id], )]  # current user is attendee
        })
        event.write({'start': date(2020, 1, 7), 'stop': date(2020, 1, 8)})
        # To avoid 403 errors, we send a limited dictionnary when we don't have write access.
        # guestsCanModify property is not properly handled yet
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'start': {'date': str(event.start_date), 'dateTime': None},
            'end': {'date': str(event.stop_date + relativedelta(days=1)), 'dateTime': None},
            'summary': 'coucou',
            'description': '',
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'c.c@example.com', 'self': False},
            'attendees': [{'email': 'c.c@example.com', 'responseStatus': 'needsAction'},
                          {'email': 'odoobot@example.com', 'responseStatus': 'accepted'},],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id,
                                              '%s_owner_id' % self.env.cr.dbname: other_user.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'visibility': 'public',
            'transparency': 'opaque',
        }, timeout=3)

    @patch_api
    def test_attendee_recurrence_answer(self):
        """ Write on a recurrence to update all attendee answers """
        other_user = new_test_user(self.env, login='calendar-user')
        google_id = "aaaaaaaaaaa"
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': datetime(2021, 2, 15, 7, 0, 0),
            'stop': datetime(2021, 2, 15, 9, 0, 0),
            'event_tz': 'Europe/Brussels',
            'need_sync': False,
            'partner_ids': [(6, 0, [other_user.partner_id.id])]
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        recurrence.calendar_event_ids.attendee_ids.state = 'accepted'
        values = {
            'id': google_id,
            "updated": self.now,
            'description': '',
            'attendees': [{'email': 'c.c@example.com', 'responseStatus': 'declined'}],
            'summary': 'coucou',
            # 'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'dateTime': '2021-02-15T8:00:00+01:00', 'timeZone': 'Europe/Brussels'},
            'end': {'dateTime': '2021-02-15T10:00:00+01:00', 'timeZone': 'Europe/Brussels'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        attendee = recurrence.calendar_event_ids.attendee_ids.mapped('state')
        self.assertEqual(attendee, ['declined', 'declined', 'declined'], "All events should be declined")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_creation_with_attendee_answer(self):
        """ Create a recurrence with predefined attendee answers """
        google_id = "aaaaaaaaaaa"
        values = {
            'id': google_id,
            "updated": self.now,
            'description': '',
            'attendees': [{'email': 'c.c@example.com', 'responseStatus': 'declined'}],
            'summary': 'coucou',
            # 'visibility': 'public',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'dateTime': '2021-02-15T8:00:00+01:00', 'timeZone': 'Europe/Brussels'},
            'end': {'dateTime': '2021-02-15T10:00:00+01:00', 'timeZone': 'Europe/Brussels'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', google_id)])
        attendee = recurrence.calendar_event_ids.attendee_ids.mapped('state')
        self.assertEqual(attendee, ['declined', 'declined', 'declined'], "All events should be declined")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_several_attendee_have_the_same_mail(self):
        """
        In google, One mail = One attendee but on Odoo, some partners could share the same mail
        This test checks that the deletion of such attendee has no harm: all attendee but the given mail are deleted.
        """
        partner1 = self.env['res.partner'].create({
            'name': 'joe',
            'email': 'dalton@example.com',
        })
        partner2 = self.env['res.partner'].create({
            'name': 'william',
            'email': 'dalton@example.com',
        })
        partner3 = self.env['res.partner'].create({
            'name': 'jack',
            'email': 'dalton@example.com',
        })
        partner4 = self.env['res.partner'].create({
            'name': 'averell',
            'email': 'dalton@example.com',
        })
        google_id = "aaaaaaaaaaaaaaaaa"
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': datetime(2020, 1, 13, 16, 0),
            'stop': datetime(2020, 1, 13, 20),
            'allday': False,
            'google_id': google_id,
            'need_sync': False,
            'user_id': self.env.user.partner_id.id,
            'partner_ids': [(6, 0, [self.env.user.partner_id.id, partner1.id, partner2.id, partner3.id, partner4.id],)]
            # current user is attendee
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=MO',
            'need_sync': False,
            'base_event_id': event.id,
            'calendar_event_ids': [(4, event.id)],
        })
        recurrence._apply_recurrence()
        recurrence.calendar_event_ids.attendee_ids.state = 'accepted'
        mails = sorted(set(event.attendee_ids.mapped('email')))
        self.assertEqual(mails, ['dalton@example.com', 'odoobot@example.com'])
        gevent = GoogleEvent([{
            'id': google_id,
            'description': 'coucou',
            "updated": self.now,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'summary': False,
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id, }},
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=3;BYDAY=MO'],
            'start': {
                'dateTime': '2020-01-13T16:00:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T20:00:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }])
        self.sync(gevent)
        # User attendee removed but gevent owner might be added after synch.
        mails = event.attendee_ids.mapped('email')
        self.assertFalse(mails)

        self.assertGoogleAPINotCalled()

    def test_several_users_have_the_same_mail(self):
        # We want to chose the internal user
        user1 = new_test_user(self.env, login='test@example.com', groups='base.group_portal')
        user2 = new_test_user(self.env, login='calendar-user2')
        user2.partner_id.email = 'test@example.com'
        user1.partner_id.name = "A First in alphabet"
        user2.partner_id.name = "B Second in alphabet"
        values = {
            'id': "abcd",
            'description': 'coucou',
            "updated": self.now,
            'organizer': {'email': 'odoobot@example.com', 'self': True},
            'summary': False,
            'visibility': 'public',
            'attendees': [{'email': 'test@example.com', 'responseStatus': 'accepted'}, {'email': 'test2@example.com', 'responseStatus': 'accepted'}],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:00:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T20:00:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        event = self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        new_partner = self.env['res.partner'].search([('email', '=', 'test2@example.com')])
        self.assertEqual(event.partner_ids.ids, [user2.partner_id.id, new_partner.id], "The internal user should be chosen")

    @patch_api
    def test_event_with_meeting_url(self):
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            },],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'conferenceData': {
                'entryPoints': [{
                    'entryPointType': 'video',
                    'uri': 'https://meet.google.com/odoo-random-test',
                    'label': 'meet.google.com/odoo-random-test'
                }, {
                    'entryPointType': 'more',
                    'uri':'https://tel.meet/odoo-random-test?pin=42424242424242',
                    'pin':'42424242424242'
                }]
            }
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(event, "It should have created an event")
        self.assertEqual(event.videocall_location, 'https://meet.google.com/odoo-random-test')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_event_with_local_videocall(self):
        """This makes sure local video call is not discarded if google's meeting url is False"""
        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        event = self.env['calendar.event'].create({
            'name': 'coucou',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'google_id': google_id,
            'user_id': self.env.user.id,
            'need_sync': False,
            'partner_ids': [(6, 0, self.env.user.partner_id.ids)],
            'videocall_location': 'https://meet.google.com/odoo_local_videocall',
        })
        values = {
            'id': google_id,
            'status': 'confirmed',
            'description': 'Event without meeting url',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Event without meeting url',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            },],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'conferenceData': {
                'entryPoints': [{
                    'entryPointType': 'video',
                    'uri': False,
                    'label': 'no label'
                }]
            },
            'updated': self.now,
        }
        # make sure local video call is not discarded
        gevent = GoogleEvent([values])
        self.env['calendar.event']._sync_google2odoo(gevent)
        self.assertEqual(event.videocall_location, 'https://meet.google.com/odoo_local_videocall')

        # now google has meet URL and make sure local video call is updated accordingly
        values['conferenceData']['entryPoints'][0]['uri'] = 'https://meet.google.com/odoo-random-test'
        gevent = GoogleEvent([values])
        self.env['calendar.event']._sync_google2odoo(gevent)
        self.assertEqual(event.videocall_location, 'https://meet.google.com/odoo-random-test')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_event_with_availability(self):
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            },],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'transparency': 'transparent'
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertTrue(event, "It should have created an event")
        self.assertEqual(event.show_as, 'free')
        self.assertGoogleAPINotCalled

    @patch_api
    def test_private_partner_single_event(self):
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }, {
                'displayName': 'Attendee',
                'email': self.private_partner.email,
                'responseStatus': 'needsAction'
            }, ],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }

        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        private_attendee = event.attendee_ids.filtered(lambda e: e.email == self.private_partner.email)
        self.assertNotEqual(self.private_partner.id, private_attendee.partner_id.id)
        self.assertNotEqual(private_attendee.partner_id.type, 'private')
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_private_contact(self):
        recurrence_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        values = {
            'id': recurrence_id,
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Attendee',
                'email': self.private_partner.email,
                'responseStatus': 'needsAction'
            }, ],
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=3;BYDAY=MO'],
            'reminders': {'useDefault': True},
            'start': {'date': '2020-01-6'},
            'end': {'date': '2020-01-7'},
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        recurrence = self.env['calendar.recurrence'].search([('google_id', '=', values.get('id'))])
        events = recurrence.calendar_event_ids
        private_attendees = events.mapped('attendee_ids').filtered(lambda e: e.email == self.private_partner.email)
        self.assertTrue(all([a.partner_id.id != self.private_partner.id for a in private_attendees]))
        self.assertTrue(all([a.partner_id.type != 'private' for a in private_attendees]))
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_alias_email_sync_recurrence(self):
        catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        alias_model = self.env['ir.model'].search([('model', '=', 'calendar.event')])
        self.env['mail.alias'].create({'alias_name': 'sale', 'alias_model_id': alias_model.id})
        alias_email = 'sale@%s' % catchall_domain if catchall_domain else 'sale@'

        google_id = 'oj44nep1ldf8a3ll02uip0c9aa'
        base_event = self.env['calendar.event'].create({
            'name': 'coucou',
            'allday': True,
            'start': datetime(2020, 1, 6),
            'stop': datetime(2020, 1, 6),
            'need_sync': False,
            'user_id': self.env.uid
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=2;BYDAY=MO',
            'need_sync': False,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        })
        recurrence._apply_recurrence()
        values = {
            'id': google_id,
            'summary': 'coucou',
            'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=2;BYDAY=MO'],
            'start': {'date': '2020-01-06'},
            'end': {'date': '2020-01-07'},
            'reminders': {'useDefault': True},
            "attendees": [
                {
                    "email": alias_email, "state": "accepted",
                },
            ],
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2)
        # Only the event organizer must remain as attendee.
        self.assertEqual(len(events.mapped('attendee_ids')), 1)
        self.assertEqual(events.mapped('attendee_ids')[0].partner_id, self.env.user.partner_id)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_owner_only_new_google_event(self):
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }
        self.env['calendar.event']._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertEqual(1, len(event.attendee_ids))
        self.assertEqual(event.partner_ids[0], event.attendee_ids[0].partner_id)
        self.assertEqual('accepted', event.attendee_ids[0].state)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_partner_order(self):
        self.private_partner.email = "internal_user@odoo.com"
        self.private_partner.type = "contact"
        user = self.env['res.users'].create({
            'name': 'Test user Calendar',
            'login': self.private_partner.email,
            'partner_id': self.private_partner.id,
            'type': 'contact'
        })
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'internal_user@odoo.com'},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': self.public_partner.email,
                'responseStatus': 'needsAction'
            }, {
                'displayName': 'Attendee',
                'email': self.private_partner.email,
                'responseStatus': 'needsAction',
                'self': True,
            }, ],
            'reminders': {'useDefault': True},
            'start': {
                'dateTime': '2020-01-13T16:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
            'end': {
                'dateTime': '2020-01-13T19:55:00+01:00',
                'timeZone': 'Europe/Brussels'
            },
        }

        self.env['calendar.event'].with_user(user)._sync_google2odoo(GoogleEvent([values]))
        event = self.env['calendar.event'].search([('google_id', '=', values.get('id'))])
        self.assertEqual(2, len(event.partner_ids), "Two attendees and two partners should be associated to the event")
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_range_start_date_in_other_dst_period(self):
        """
            It is possible to create recurring events that are in the same DST period
            but when calculating the start date for the range, it is possible to change the dst period.
            This results in a duplication of the basic event.
        """
        # DST change: 2023-03-26
        frequency = "MONTHLY"
        count = "1" # Just to go into the flow of the recurrence
        recurrence_id = "9lxiofipomymx2yr1yt0hpep99"
        google_value = [{
                "summary": "Start date in DST period",
                "id": recurrence_id,
                "creator": {"email": "john.doe@example.com"},
                "organizer": {"email": "john.doe@example.com"},
                "created": "2023-03-27T11:45:07.000Z",
                "start": {"dateTime": "2023-03-27T09:00:00+02:00", "timeZone": "Europe/Brussels"},
                "end": {"dateTime": "2023-03-27T10:00:00+02:00", "timeZone": "Europe/Brussels"},
                "recurrence": [f"RRULE:FREQ={frequency};COUNT={count}"],
                "reminders": {"useDefault": True},
                "updated": "2023-03-27T11:45:08.547Z",
            }]
        google_event = GoogleEvent(google_value)
        self.env['calendar.recurrence']._sync_google2odoo(google_event)
        # Get the time slot of the day
        day_start = datetime.fromisoformat(google_event.start["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=0)
        day_end = datetime.fromisoformat(google_event.end["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=23)
        # Get created events
        day_events = self.env["calendar.event"].search(
            [
                ("name", "=", google_event.summary),
                ("start", ">=", day_start),
                ("stop", "<=", day_end)
            ]
        )
        self.assertGoogleAPINotCalled()
        # Check for non-duplication
        self.assertEqual(len(day_events), 1)

    @patch_api
    def test_recurrence_edit_specific_event(self):
        google_values = [
            {
                'kind': 'calendar#event',
                'etag': '"3367067678542000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:19.271Z',
                'summary': 'First title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-12T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-12T10:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20230518T215959Z;BYDAY=FR'],
                'iCalUID': '59orfkiunbn2vlp6c2tndq6ui0@google.com',
                'reminders': {'useDefault': True},
            },
            {
                'kind': 'calendar#event',
                'etag': '"3367067678542000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:19.271Z',
                'summary': 'Second title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-19T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-19T10:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=2;BYDAY=FR'],
                'iCalUID': '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000@google.com',
                'reminders': {'useDefault': True},
            },
            {
                'kind': 'calendar#event',
                'etag': '"3367067704194000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0_20230526T070000Z',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:32.097Z',
                'summary': 'Second title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-26T08:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-26T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurringEventId': '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000',
                'originalStartTime': {'dateTime': '2023-05-26T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'reminders': {'useDefault': True},
            }
        ]
        google_events = GoogleEvent(google_values)

        recurrent_events = google_events.filter(lambda e: e.is_recurrence())
        specific_event = google_events - recurrent_events
        # recurrence_event: 59orfkiunbn2vlp6c2tndq6ui0 and 59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000
        # specific_event: 59orfkiunbn2vlp6c2tndq6ui0_20230526T070000Z

        # Range to check
        day_start = datetime.fromisoformat(specific_event.start["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=0)
        day_end = datetime.fromisoformat(specific_event.end["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=23)

        # Synchronize recurrent events
        self.env['calendar.recurrence']._sync_google2odoo(recurrent_events)
        events = self.env["calendar.event"].search(
            [
                ("name", "=", specific_event.summary),
                ("start", ">=", day_start),
                ("stop", "<=", day_end,)
            ]
        )
        self.assertEqual(len(events), 1)

        # Events:
        # 'First title' --> '59orfkiunbn2vlp6c2tndq6ui0_20230512T070000Z'
        # 'Second title' --> '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000_20230519T070000Z'
        # 'Second title' --> '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000_20230526T070000Z'

        # We want to apply change on '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000_20230526T070000Z'
        # with values from '59orfkiunbn2vlp6c2tndq6ui0_20230526T070000Z'

        # To match the google ids, we create a new event and delete the old one to avoid duplication

        # Synchronize specific event
        self.env['calendar.event']._sync_google2odoo(specific_event)
        events = self.env["calendar.event"].search(
            [
                ("name", "=", specific_event.summary),
                ("start", ">=", day_start),
                ("stop", "<=", day_end,)
            ]
        )
        self.assertEqual(len(events), 1)

        # Not call API
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_recurrence_edit_specific_event_backward_compatibility(self):
        """
            Check that the creation of full recurrence ids does not crash
            to avoid event duplication.
            Note 1:
                Not able to reproduce the payload in practice.
                However, it exists in production.
            Note 2:
                This is the same test as 'test_recurrence_edit_specific_event',
                with the range in 'recurringEventId' removed for the specific event.
        """
        google_values = [
            {
                'kind': 'calendar#event',
                'etag': '"3367067678542000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:19.271Z',
                'summary': 'First title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-12T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-12T10:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20230518T215959Z;BYDAY=FR'],
                'iCalUID': '59orfkiunbn2vlp6c2tndq6ui0@google.com',
                'reminders': {'useDefault': True},
            },
            {
                'kind': 'calendar#event',
                'etag': '"3367067678542000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:19.271Z',
                'summary': 'Second title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-19T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-19T10:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;COUNT=2;BYDAY=FR'],
                'iCalUID': '59orfkiunbn2vlp6c2tndq6ui0_R20230519T070000@google.com',
                'reminders': {'useDefault': True},
            },
            {
                'kind': 'calendar#event',
                'etag': '"3367067704194000"',
                'id': '59orfkiunbn2vlp6c2tndq6ui0_20230526T070000Z',
                'status': 'confirmed',
                'created': '2023-05-08T08:16:54.000Z',
                'updated': '2023-05-08T08:17:32.097Z',
                'summary': 'Second title',
                'creator': {'email': 'john.doe@example.com', 'self': True},
                'organizer': {'email': 'john.doe@example.com', 'self': True},
                'start': {'dateTime': '2023-05-26T08:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'end': {'dateTime': '2023-05-26T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'recurringEventId': '59orfkiunbn2vlp6c2tndq6ui0', # Range removed
                'originalStartTime': {'dateTime': '2023-05-26T09:00:00+02:00', 'timeZone': 'Europe/Brussels'},
                'reminders': {'useDefault': True},
            }
        ]
        google_events = GoogleEvent(google_values)

        recurrent_events = google_events.filter(lambda e: e.is_recurrence())
        specific_event = google_events - recurrent_events
        # Range to check
        day_start = datetime.fromisoformat(specific_event.start["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=0)
        day_end = datetime.fromisoformat(specific_event.end["dateTime"]).astimezone(pytz.utc).replace(tzinfo=None).replace(hour=23)

        # Synchronize recurrent events
        self.env['calendar.recurrence']._sync_google2odoo(recurrent_events)
        events = self.env["calendar.event"].search(
            [
                ("name", "=", specific_event.summary),
                ("start", ">=", day_start),
                ("stop", "<=", day_end,)
            ]
        )
        self.assertEqual(len(events), 1)

        # Synchronize specific event
        self.env['calendar.event']._sync_google2odoo(specific_event)
        events = self.env["calendar.event"].search(
            [
                ("name", "=", specific_event.summary),
                ("start", ">=", day_start),
                ("stop", "<=", day_end,)
            ]
        )
        self.assertEqual(len(events), 2) # Two because in this case we does not detect the existing event
        # The stream is not blocking, but there is a duplicate

        # Not call API
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_attendee_status_is_not_updated_when_syncing_and_time_data_is_not_changed(self):
        recurrence_id = "aaaaaaaa"
        organizer = new_test_user(self.env, login="organizer")
        other_user = new_test_user(self.env, login='calendar_user')
        base_event = self.env['calendar.event'].with_user(organizer).create({
            'name': 'coucou',
            'start': datetime(2020, 1, 6, 9, 0),
            'stop': datetime(2020, 1, 6, 10, 0),
            'need_sync': False,
            'partner_ids': [Command.set([organizer.partner_id.id, other_user.partner_id.id])]
        })
        recurrence = self.env['calendar.recurrence'].with_user(organizer).create({
            'google_id': recurrence_id,
            'rrule': 'FREQ=DAILY;INTERVAL=1;COUNT=3',
            'need_sync': False,
            'base_event_id': base_event.id,
        })
        recurrence._apply_recurrence()

        self.assertTrue(all(len(event.attendee_ids) == 2 for event in recurrence.calendar_event_ids), 'should have 2 attendees in all recurring events')
        organizer_state = recurrence.calendar_event_ids.sorted('start')[0].attendee_ids.filtered(lambda attendee: attendee.partner_id.email == organizer.partner_id.email).state
        self.assertEqual(organizer_state, 'accepted', 'organizer should have accepted')
        values = [{
            'summary': 'coucou',
            'id': recurrence_id,
            'recurrence': ['RRULE:FREQ=DAILY;INTERVAL=1;COUNT=3'],
            'start': {'dateTime': '2020-01-06T10:00:00+01:00'},
            'end': {'dateTime': '2020-01-06T11:00:00+01:00'},
            'reminders': {'useDefault': True},
            'organizer': {'email': organizer.partner_id.email},
            'attendees': [{'email': organizer.partner_id.email, 'responseStatus': 'accepted'}, {'email': other_user.partner_id.email, 'responseStatus': 'accepted'}],
            'updated': self.now,
        }]
        self.env['calendar.recurrence'].with_user(other_user)._sync_google2odoo(GoogleEvent(values))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "it should have created a recurrence with 3 events")
        self.assertEqual(events[0].attendee_ids[0].state, 'accepted', 'after google sync, organizer should have accepted status still')
        self.assertGoogleAPINotCalled()

    @patch.object(GoogleCalendarService, "get_events")
    def test_recurring_event_moved_to_future(self, mock_get_events):
        # There's a daily recurring event from 2024-07-01 to 2024-07-02
        recurrence_id = "abcd1"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-07-01",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=2",
            start=datetime(2024, 7, 1, 9),
            stop=datetime(2024, 7, 1, 10),
            partner_ids=[
                Command.set(
                    [
                        self.organizer_user.partner_id.id,
                        self.attendee_user.partner_id.id,
                    ]
                )
            ],
        )
        self.assertRecordValues(
            recurrence.calendar_event_ids.sorted("start"),
            [
                {
                    "start": datetime(2024, 7, 1, 9),
                    "stop": datetime(2024, 7, 1, 10),
                    "google_id": f"{recurrence_id}_20240701T090000Z",
                },
                {
                    "start": datetime(2024, 7, 2, 9),
                    "stop": datetime(2024, 7, 2, 10),
                    "google_id": f"{recurrence_id}_20240702T090000Z",
                },
            ],
        )
        # User moves batch to next week
        common = {
            "attendees": [
                {
                    "email": self.attendee_user.partner_id.email,
                    "responseStatus": "needsAction",
                },
                {
                    "email": self.organizer_user.partner_id.email,
                    "responseStatus": "needsAction",
                },
            ],
            "organizer": {"email": self.organizer_user.partner_id.email},
            "reminders": {"useDefault": True},
            "summary": "coucou",
            "updated": "2024-07-02T08:00:00Z",
        }
        google_events = [
            # Recurrence event
            dict(
                common,
                id=recurrence_id,
                start={"dateTime": "2024-07-08T09:00:00+00:00"},
                end={"dateTime": "2024-07-08T10:00:00+00:00"},
                recurrence=["RRULE:FREQ=DAILY;INTERVAL=1;COUNT=2"],
            ),
            # Cancelled instances
            {"id": f"{recurrence_id}_20240701T090000Z", "status": "cancelled"},
            {"id": f"{recurrence_id}_20240702T090000Z", "status": "cancelled"},
            # New base event
            dict(
                common,
                id=f"{recurrence_id}_20240708T090000Z",
                start={"dateTime": "2024-07-08T09:00:00+00:00"},
                end={"dateTime": "2024-07-08T10:00:00+00:00"},
                recurringEventId=recurrence_id,
            ),
        ]
        mock_get_events.return_value = (
            GoogleEvent(google_events),
            None,
            [{"method": "popup", "minutes": 30}],
        )
        with self.mock_datetime_and_now("2024-04-03"):
            self.organizer_user.sudo()._sync_google_calendar(self.google_service)
            self.assertRecordValues(
                recurrence.calendar_event_ids.sorted("start"),
                [
                    {
                        "start": datetime(2024, 7, 8, 9),
                        "stop": datetime(2024, 7, 8, 10),
                        "google_id": f"{recurrence_id}_20240708T090000Z",
                    },
                    {
                        "start": datetime(2024, 7, 9, 9),
                        "stop": datetime(2024, 7, 9, 10),
                        "google_id": f"{recurrence_id}_20240709T090000Z",
                    },
                ],
            )

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_this_event_option_synced_by_attendee(self, mock_get_events):
        """
        Test accepting a recurring event with the option "This event" on Google Calendar and syncing the attendee's calendar.
        Ensure that event is accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd1"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_this_event(recurrence, 2, 'accepted')
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["needsAction", "needsAction", "accepted", "needsAction"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.attendee_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_this_event_option_synced_by_organizer(self, mock_get_events):
        """
        Test accepting a recurring event with the option "This event" on Google Calendar and syncing the organizer's calendar.
        Ensure that event is accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd2"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_this_event(recurrence, 2, 'accepted')
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["needsAction", "needsAction", "accepted", "needsAction"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.organizer_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_all_events_option_synced_by_attendee(self, mock_get_events):
        """
        Test accepting a recurring event with the option "All events" on Google Calendar and syncing the attendee's calendar.
        Ensure that all events are accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd3"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_all_events(recurrence, "accepted")
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["accepted", "accepted", "accepted", "accepted"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.attendee_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_all_events_option_synced_by_organizer(self, mock_get_events):
        """
        Test accepting a recurring event with the option "All events" on Google Calendar and syncing the organizer's calendar.
        Ensure that all events are accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd4"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_all_events(recurrence, "accepted")
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["accepted", "accepted", "accepted", "accepted"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.organizer_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_following_events_option_synced_by_attendee(self, mock_get_events):
        """
        Test accepting a recurring event with the option "This and following events" on Google Calendar and syncing the attendee's calendar.
        Ensure that affected events are accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd5"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_following_events(
            recurrence=recurrence,
            event_index=2,
            response_status="accepted",
            rrule1="RRULE:FREQ=DAILY;UNTIL=20240321T215959Z",
            rrule2="RRULE:FREQ=DAILY;COUNT=2"
        )
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["needsAction", "needsAction", "accepted", "accepted"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.attendee_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch.object(GoogleCalendarService, 'get_events')
    def test_accepting_recurrent_event_with_all_following_option_synced_by_organizer(self, mock_get_events):
        """
        Test accepting a recurring event with the option "This and following events" on Google Calendar and syncing the organizer's calendar.
        Ensure that affected events are accepeted by attendee in Odoo.
        """
        recurrence_id = "abcd6"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-20",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 3, 20, 9, 0),
            stop=datetime(2024, 3, 20, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])],
        )
        google_events = self.google_respond_to_recurrent_event_with_option_following_events(
            recurrence=recurrence,
            event_index=2,
            response_status="accepted",
            rrule1="RRULE:FREQ=DAILY;UNTIL=20240321T215959Z",
            rrule2="RRULE:FREQ=DAILY;COUNT=2"
        )
        mock_get_events.return_value = (
            GoogleEvent(google_events), None, [{'method': 'popup', 'minutes': 30}]
        )
        expected_states = ["needsAction", "needsAction", "accepted", "accepted"]
        with self.mock_datetime_and_now("2024-04-22"):
            self.organizer_user.sudo()._sync_google_calendar(self.google_service)
            attendees = self.env['calendar.attendee'].search([
                ('partner_id', '=', self.attendee_user.partner_id.id)
            ]).sorted(key=lambda r: r.event_id.start)
            for i, expected_state in enumerate(expected_states):
                self.assertEqual(attendees[i].state, expected_state)

    @patch_api
    def test_keep_organizer_attendee_writing_recurrence_from_google(self):
        """
        When receiving recurrence updates from google in 'write_from_google', make
        sure the organizer is kept as attendee of the events. This will guarantee
        that the newly updated events will not disappear from the calendar view.
        """
        def check_organizer_as_single_attendee(self, recurrence, organizer):
            """ Ensure that the organizer is the single attendee of the recurrent events. """
            for event in recurrence.calendar_event_ids:
                self.assertTrue(len(event.attendee_ids) == 1, 'Should have only one attendee.')
                self.assertEqual(event.attendee_ids[0].partner_id, organizer.partner_id, 'The single attendee must be the organizer.')

        # Generate a regular recurrence with only the organizer as attendee.
        recurrence_id = "rec_id"
        recurrence = self.generate_recurring_event(
            mock_dt="2024-04-10",
            google_id=recurrence_id,
            rrule="FREQ=DAILY;INTERVAL=1;COUNT=4",
            start=datetime(2024, 4, 11, 9, 0),
            stop=datetime(2024, 4, 11, 10, 0),
            partner_ids=[Command.set([self.organizer_user.partner_id.id])],
        )
        check_organizer_as_single_attendee(self, recurrence, self.organizer_user)

        # Update the recurrence without specifying its attendees, the organizer must be kept as
        # attendee after processing it, thus the new events will be kept in its calendar view.
        values = [{
            'summary': 'updated_rec',
            'id': recurrence_id,
            'recurrence': ['RRULE:FREQ=DAILY;INTERVAL=1;COUNT=3'],
            'start': {'dateTime': '2024-04-13T8:00:00+01:00'},
            'end': {'dateTime': '2024-04-13T9:00:00+01:00'},
            'reminders': {'useDefault': True},
            'organizer': {'email': self.organizer_user.partner_id.email},
            'attendees': [],
            'updated': self.now,
        }]
        self.env['calendar.recurrence'].with_user(self.organizer_user)._sync_google2odoo(GoogleEvent(values))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3, "The new recurrence must have three events.")
        check_organizer_as_single_attendee(self, recurrence, self.organizer_user)
        self.assertGoogleAPINotCalled()
