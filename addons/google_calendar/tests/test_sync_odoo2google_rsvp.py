# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.tests import tagged


@tagged('odoo2google')
@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncOdoo2GoogleRSVP(TestSyncGoogle):

    def _create_synced_recurrence(self, google_id='test-google-id'):
        base_event = self.env['calendar.event'].create({
            'name': "Event with attendees",
            'start': datetime(2020, 1, 15),
            'stop': datetime(2020, 1, 15),
            'allday': True,
            'need_sync': False,
            'partner_ids': [(4, self.attendee_user.partner_id.id), (4, self.env.user.partner_id.id)],
            'recurrency': True,
            'follow_recurrence': True,
        })
        recurrence = self.env['calendar.recurrence'].create({
            'google_id': google_id,
            'rrule': 'FREQ=WEEKLY;COUNT=3;BYDAY=WE',
            'base_event_id': base_event.id,
            'need_sync': False,
        })
        recurrence._apply_recurrence()
        self.assertEqual(
            recurrence.calendar_event_ids.sorted('start').mapped('google_id'),
            [f'{google_id}_20200115', f'{google_id}_20200122', f'{google_id}_20200129'],
            "Each event's google_id should be derived from the recurrence's google_id",
        )
        return recurrence

    @patch_api
    def test_updating_recurrence_single_patch(self):
        """ Updating a whole recurrence chain must only patch the master recurrence once.
        Google then propagates the change to every instance. """
        recurrence_google_id = 'rrrrrrrrr'
        recurrence = self._create_synced_recurrence(recurrence_google_id)
        recurrence.calendar_event_ids.attendee_ids.with_context(recurrence_update_setting='all_events').do_decline()

        # Exactly one patch must have been issued, targeting the master recurrence.
        self.assertEqual(
            sum(len(values) for values in self._gsync_patch_values.values()), 1,
            "Only the master recurrence should be patched when updating all events of a chain"
        )
        self.assertIn(recurrence_google_id, self._gsync_patch_values, "The patch must target the master recurrence's google_id")

    @patch_api
    def test_updating_recurrence_single_instance_patch(self):
        """ Updating a single instance of a recurrence chain must only patch that instance, not the master recurrence. """
        recurrence_google_id = 'rrrrrrrrr'
        recurrence = self._create_synced_recurrence(recurrence_google_id)

        # RSVP on a single instance of the chain (it still follows the recurrence).
        instance = recurrence.calendar_event_ids.sorted('start')[1]
        self.assertTrue(instance.follow_recurrence)
        instance.attendee_ids.with_context(recurrence_update_setting='self_only').do_decline()

        # Exactly one patch must have been issued, targeting the instance, never the master recurrence.
        self.assertEqual(
            sum(len(values) for values in self._gsync_patch_values.values()), 1,
            "Only the updated instance should be patched when updating a single event of a chain"
        )
        self.assertIn(instance.google_id, self._gsync_patch_values, "The patch must target the instance's google_id")
        self.assertNotIn(recurrence_google_id, self._gsync_patch_values, "The master recurrence must not be patched")

    @patch_api
    def test_updating_future_events_breaks_recurrence(self):
        """ RSVP on "this and following": the old master is trimmed once, the tail
        becomes a new recurrence inserted once, and no instance is patched. """
        recurrence_google_id = 'rrrrrrrrr'
        recurrence = self._create_synced_recurrence(recurrence_google_id)
        first, second, third = recurrence.calendar_event_ids.sorted('start')
        instance_ids = recurrence.calendar_event_ids.mapped('google_id')

        self.env.user.partner_id = second.attendee_ids.mapped('partner_id')[0]
        second.with_user(self.attendee_user).change_attendee_status('declined', 'future_events')

        new_recurrence = second.recurrence_id
        self.assertNotEqual(new_recurrence, recurrence)
        self.assertEqual(recurrence.calendar_event_ids, first)
        self.assertEqual(new_recurrence.calendar_event_ids, second | third)
        self.assertEqual(first.attendee_ids[0].state, 'needsAction')
        self.assertEqual((second | third).attendee_ids.mapped('state'), ['declined', 'declined'])
        self.assertEqual(len(self._gsync_insert_values), 1, "New master inserted once")
        self.assertGoogleEventPatched(recurrence_google_id, {
            'id': recurrence_google_id,
            'start': {'date': '2020-01-15', 'dateTime': None},
            'end': {'date': '2020-01-16', 'dateTime': None},
            'summary': 'Event with attendees',
            'description': first.description,
            'location': '',
            'guestsCanModify': True,
            'organizer': {'email': 'a.a@example.com', 'self': False},
            'attendees': [{'email': 'a.a@example.com', 'responseStatus': 'needsAction'}, {'email': 'odoobot@example.com', 'responseStatus': 'accepted'}],
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: recurrence.id}},
            'reminders': {'overrides': [], 'useDefault': False},
            'conferenceData': None,
            'recurrence': ['RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20200118T235959Z;BYDAY=WE'],
            'transparency': 'opaque'
        }, timeout=3)
        for google_id in instance_ids:
            self.assertNotIn(google_id, self._gsync_patch_values, "No instance may be patched individually")
