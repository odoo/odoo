# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.google_calendar.utils.google_calendar import GoogleEvent
import pytz
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import new_test_user
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api


class TestSyncGoogle2Odoo(TestSyncGoogle):

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
        values = {
            'id': 'oj44nep1ldf8a3ll02uip0c9aa',
            'description': 'Small mini desc',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'summary': 'Pricing new update',
            'visibility': 'public',
            'attendees': [{
                'displayName': 'Mitchell Admin',
                'email': 'admin@yourcompany.example.com',
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
        self.assertEqual(event.description, values.get('description'))
        self.assertEqual(event.start, datetime(2020, 1, 13, 15, 55))
        self.assertEqual(event.stop, datetime(2020, 1, 13, 18, 55))
        admin_attendee = event.attendee_ids.filtered(lambda e: e.email == 'admin@yourcompany.example.com')
        self.assertEqual('admin@yourcompany.example.com', admin_attendee.email)
        self.assertEqual('Mitchell Admin', admin_attendee.partner_id.name)
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
        gevent = GoogleEvent([{
            'id': google_id,
            'status': 'cancelled',
        }])
        self.sync(gevent)
        self.assertTrue(event.active)
        user_attendee = event.attendee_ids
        self.assertTrue(user_attendee)
        self.assertEqual(user_attendee.state, 'declined')
        # To avoid 403 errors, we send a limited dictionnary when we don't have write access.
        # guestsCanModify property is not properly handled yet
        self.assertGoogleEventPatched(event.google_id, {
            'id': event.google_id,
            'start': {'date': str(event.start_date)},
            'end': {'date': str(event.stop_date + relativedelta(days=1))},
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
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2)
        self.assertEqual(recurrence.rrule, 'FREQ=WEEKLY;COUNT=2;BYDAY=WE')
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
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 2)
        self.assertEqual(recurrence.rrule, 'FREQ=WEEKLY;COUNT=2;BYDAY=MO')
        self.assertEqual(events.mapped('name'), ['coucou again','coucou again'])
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
            'updated': self.now,
        }
        self.env['calendar.recurrence']._sync_google2odoo(GoogleEvent([values]))
        events = recurrence.calendar_event_ids.sorted('start')
        self.assertEqual(len(events), 3)
        self.assertEqual(recurrence.rrule, 'FREQ=WEEKLY;COUNT=3;BYDAY=MO')
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
                'email': 'admin@yourcompany.example.com',
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
