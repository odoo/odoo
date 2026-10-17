from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo.exceptions import UserError
from odoo.addons.microsoft_calendar.models.microsoft_sync import MicrosoftSync
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.tests.common import TestCommon, patch_api


class TestMicrosoftIncomingMissingUid(TestCommon):

    def _create_linked_activity(self, event):
        return self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.attendee_user.partner_id.id,
            'user_id': self.attendee_user.id,
            'calendar_event_id': event.id,
        })

    def _assert_records_survive(self, records, activity):
        self.env.flush_all()
        self.env.invalidate_all()
        for name, record in records.items():
            with self.subTest(record=name):
                self.assertEqual(record.exists(), record, f'{name} must survive incoming sync')
        # Check the actual row too: event deletion can cascade to mail.activity.
        with self.subTest(record='activity SQL row'):
            self.env.cr.execute('SELECT id FROM mail_activity WHERE id = %s', [activity.id])
            self.assertEqual(self.env.cr.fetchall(), [(activity.id,)])

    @patch_api
    def test_missing_master_uid_preserves_unrelated_single(self):
        # With no valid master UID in the batch, cleanup must leave local singles untouched.
        event_model = self.env['calendar.event'].with_user(self.attendee_user).with_context(dont_notify=True)
        unrelated = event_model.create({
            **self.simple_event_values,
            'name': 'Unrelated local single',
            'user_id': self.attendee_user.id,
            'partner_ids': [(6, 0, self.attendee_user.partner_id.ids)],
        })
        activity = self._create_linked_activity(unrelated)
        control = event_model.create({
            **self.simple_event_values,
            'name': 'Single with distinct UID',
            'ms_universal_event_id': 'unrelated-single-control-uid',
        })
        records = {'unrelated event': unrelated, 'linked activity': activity, 'control event': control}
        self.assertNotEqual(unrelated.user_id, self.organizer_user)
        self.assertTrue(unrelated.active)
        self.assertFalse(unrelated.recurrence_id)
        self.assertFalse(unrelated.microsoft_id)
        self.assertFalse(unrelated.ms_universal_event_id)
        self.assertEqual(activity.calendar_event_id, unrelated)

        incoming = deepcopy(self.recurrent_event_from_outlook_organizer)
        master, = [event for event in incoming if event['type'] == 'seriesMaster']
        del master['iCalUId']
        self.env['calendar.event'].with_user(self.organizer_user).sudo().with_context(
            dont_notify=True,
        )._sync_microsoft2odoo(MicrosoftEvent(incoming))

        recurrence = self.env['calendar.recurrence'].search([('microsoft_id', '=', master['id'])])
        self.assertEqual(len(recurrence), 1, 'The valid incoming series must be created')
        self.assertFalse(recurrence.ms_universal_event_id)
        self.assertEqual(len(recurrence.calendar_event_ids), self.recurrent_events_count)
        self.assertSetEqual(
            set(recurrence.calendar_event_ids.mapped('ms_universal_event_id')),
            {event['iCalUId'] for event in incoming if event['type'] != 'seriesMaster'},
        )
        self._assert_records_survive(records, activity)

    @patch_api
    def test_removed_without_uid_preserves_unrelated_recurrence(self):
        # The syncing organizer can delete the event, so a false match also deletes its activity.
        event_model = self.env['calendar.event'].with_user(self.organizer_user).with_context(dont_notify=True)
        unrelated = event_model.create({
            **self.recurrent_event_values,
            'name': 'Unrelated local recurrence',
            'count': 1,
            'user_id': self.organizer_user.id,
        })
        recurrence = unrelated.recurrence_id
        activity = self._create_linked_activity(unrelated)
        control_event = event_model.create({
            **self.recurrent_event_values,
            'name': 'Recurrence with distinct UID',
            'count': 1,
        })
        control = control_event.recurrence_id
        control.ms_universal_event_id = 'unrelated-recurrence-control-uid'
        records = {
            'unrelated recurrence': recurrence, 'unrelated event': unrelated,
            'linked activity': activity, 'control recurrence': control, 'control event': control_event,
        }
        self.assertEqual(unrelated.user_id, self.organizer_user)
        self.assertTrue(recurrence.active)
        self.assertTrue(unrelated.active)
        self.assertEqual(recurrence.calendar_event_ids, unrelated)
        self.assertFalse(recurrence.microsoft_id)
        self.assertFalse(recurrence.ms_universal_event_id)
        self.assertEqual(activity.calendar_event_id, unrelated)
        removed_id = 'unrelated-deleted-id'
        for model in ('calendar.event', 'calendar.recurrence'):
            self.assertFalse(self.env[model].with_context(active_test=False).search([
                ('microsoft_id', '=', removed_id),
            ]))

        self.env['calendar.event'].with_user(self.organizer_user).sudo().with_context(
            dont_notify=True,
        )._sync_microsoft2odoo(MicrosoftEvent([
            {'id': removed_id, '@removed': {'reason': 'deleted'}},
        ]))

        self._assert_records_survive(records, activity)
        self.assertEqual(unrelated.recurrence_id, recurrence)
        self.assertEqual(activity.calendar_event_id, unrelated)

    @patch_api
    def test_removed_without_uid_preserves_other_organizer_recurrence(self):
        # The organizer/participant filter can spare the event while its recurrence is deleted,
        # so checking event existence alone would miss the lost recurrence link.
        unrelated = self.env['calendar.event'].with_user(self.attendee_user).with_context(
            dont_notify=True,
        ).create({
            **self.recurrent_event_values,
            'name': 'Other organizer recurrence',
            'count': 1,
            'user_id': self.attendee_user.id,
            'partner_ids': [(6, 0, self.attendee_user.partner_id.ids)],
        })
        recurrence = unrelated.recurrence_id
        activity = self._create_linked_activity(unrelated)
        organizer = unrelated.user_id
        participants = unrelated.partner_ids
        records = {
            'unrelated recurrence': recurrence, 'unrelated event': unrelated, 'linked activity': activity,
        }
        self.assertNotEqual(organizer, self.organizer_user)
        self.assertNotIn(self.organizer_user.partner_id, participants)
        self.assertTrue(recurrence.active)
        self.assertTrue(unrelated.active)
        for record in (recurrence, unrelated):
            self.assertFalse(record.microsoft_id)
            self.assertFalse(record.ms_universal_event_id)
        self.assertEqual(activity.calendar_event_id, unrelated)
        removed_id = 'unrelated-deleted-id'
        for model in ('calendar.event', 'calendar.recurrence'):
            self.assertFalse(self.env[model].with_context(active_test=False).search([
                ('microsoft_id', '=', removed_id),
            ]))

        self.env['calendar.event'].with_user(self.organizer_user).sudo().with_context(
            dont_notify=True,
        )._sync_microsoft2odoo(MicrosoftEvent([
            {'id': removed_id, '@removed': {'reason': 'deleted'}},
        ]))

        self._assert_records_survive(records, activity)
        self.assertEqual(unrelated.recurrence_id, recurrence)
        self.assertEqual(unrelated.user_id, organizer)
        self.assertEqual(unrelated.partner_ids, participants)
        self.assertEqual(activity.calendar_event_id, unrelated)

    @patch_api
    def test_removed_without_uid_matches_recurrence_by_microsoft_id(self):
        # A recognized ID must still cancel its series without affecting an independent UID-less series.
        event_model = self.env['calendar.event'].with_user(self.organizer_user).sudo().with_context(
            dont_notify=True,
        )
        incoming = deepcopy(self.recurrent_event_from_outlook_organizer)
        master, = [event for event in incoming if event['type'] == 'seriesMaster']
        event_model._sync_microsoft2odoo(MicrosoftEvent(incoming))
        recurrence = self.env['calendar.recurrence'].search([('microsoft_id', '=', master['id'])])
        self.assertEqual(len(recurrence), 1)
        self.assertEqual(recurrence.ms_universal_event_id, master['iCalUId'])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), self.recurrent_events_count)
        activity = self._create_linked_activity(events[0])

        independent = event_model.create({
            **self.recurrent_event_values,
            'name': 'Independent local recurrence',
            'count': 1,
            'user_id': self.organizer_user.id,
        })
        independent_recurrence = independent.recurrence_id
        independent_activity = self._create_linked_activity(independent)
        independent_records = {
            'independent recurrence': independent_recurrence,
            'independent event': independent,
            'independent activity': independent_activity,
        }
        for record in (independent_recurrence, independent):
            self.assertTrue(record.active)
            self.assertFalse(record.microsoft_id)
            self.assertFalse(record.ms_universal_event_id)

        event_model._sync_microsoft2odoo(MicrosoftEvent([
            {'id': master['id'], '@removed': {'reason': 'deleted'}},
        ]))

        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(recurrence.exists())
        self.assertFalse(events.exists())
        self.assertFalse(activity.exists())
        self.env.cr.execute('SELECT id FROM mail_activity WHERE id = %s', [activity.id])
        self.assertFalse(self.env.cr.fetchall())
        self._assert_records_survive(independent_records, independent_activity)
        self.assertEqual(independent.recurrence_id, independent_recurrence)
        self.assertEqual(independent_activity.calendar_event_id, independent)

    @patch_api
    def test_mixed_master_uids_only_remove_matching_single(self):
        # A missing UID must neither match local singles nor disable cleanup for valid UIDs in the batch.
        event_model = self.env['calendar.event'].with_user(self.organizer_user).sudo().with_context(
            dont_notify=True,
        )
        incoming = deepcopy(self.recurrent_event_from_outlook_organizer)
        master, = [event for event in incoming if event['type'] == 'seriesMaster']
        duplicate = event_model.create({
            **self.simple_event_values,
            'microsoft_id': master['id'],
            'ms_universal_event_id': master['iCalUId'],
        })
        unrelated = event_model.create({
            **self.simple_event_values,
            'name': 'Unrelated local single',
            'user_id': self.attendee_user.id,
            'partner_ids': [(6, 0, self.attendee_user.partner_id.ids)],
        })
        activity = self._create_linked_activity(unrelated)
        control = event_model.create({
            **self.simple_event_values,
            'name': 'Single with distinct UID',
            'ms_universal_event_id': 'mixed-batch-control-uid',
        })
        records = {'unrelated event': unrelated, 'linked activity': activity, 'control event': control}

        missing_uid_series = deepcopy(incoming)
        for event in missing_uid_series:
            event['id'] = 'missing-uid-' + event['id']
            if event['type'] == 'seriesMaster':
                del event['iCalUId']
            else:
                event['seriesMasterId'] = 'missing-uid-' + event['seriesMasterId']
                event['iCalUId'] = 'missing-uid-' + event['iCalUId']
        incoming += missing_uid_series
        event_model._sync_microsoft2odoo(MicrosoftEvent(incoming))

        for payload in incoming:
            if payload['type'] == 'seriesMaster':
                recurrence = self.env['calendar.recurrence'].search([('microsoft_id', '=', payload['id'])])
                self.assertEqual(len(recurrence), 1)
                self.assertEqual(len(recurrence.calendar_event_ids), self.recurrent_events_count)
        self.assertFalse(duplicate.exists())
        self._assert_records_survive(records, activity)


class TestMicrosoftEvent(TestCommon):

    @patch_api
    def setUp(self):
        super().setUp()
        self.create_events_for_tests()

    def test_already_mapped_events(self):

        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": self.simple_event.id,
            "iCalUId": event_uid,
            "id": event_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[event_id]["_odoo_id"], self.simple_event.id)

    def test_forbid_edit_outlook_recurring_event(self):
        """
        Test that no user can edit a recurring event imported from Outlook
        (identified by microsoft_recurrence_master_id), but that the sync
        mechanism itself can still write through via dont_notify context.
        """
        # Give the organizer user a Microsoft token
        self.organizer_user.microsoft_calendar_token = "fake_token"

        outlook_recurring_event, recurring_event = self.env['calendar.event'].with_context(dont_notify=True).create([
            {
                'name': 'Outlook Recurring Event',
                'start': datetime(2023, 9, 25, 10, 0),
                'stop': datetime(2023, 9, 25, 11, 0),
                'microsoft_id': 'AAA123:BBB456',
                'microsoft_recurrence_master_id': 'MASTER123',
                'user_id': self.organizer_user.id,
            },
            {
                'name': 'Regular Recurring Event',
                'start': datetime(2023, 9, 25, 10, 0),
                'stop': datetime(2023, 9, 25, 11, 0),
                'user_id': self.organizer_user.id,
                'partner_ids': [(4, self.organizer_user.partner_id.id)],
                'recurrency': True,
                'follow_recurrence': True,
                'rrule_type': 'daily',
                'interval': 1,
                'end_type': 'count',
                'count': 3,
            },
        ])

        # No user should be able to edit the Outlook event through Odoo
        for user in [self.attendee_user, self.organizer_user]:
            with self.assertRaises(UserError):
                outlook_recurring_event.with_user(user).with_context(dont_notify=False).write({
                    'name': 'Trying to change name',
                    'recurrence_update': 'future_events',
                })
        self.assertEqual(outlook_recurring_event.name, 'Outlook Recurring Event')

        # But changes from Microsoft sync itself should still work
        outlook_recurring_event.with_context(dont_notify=True).write({
            'name': 'Updated from Outlook',
            'recurrence_update': 'future_events'
        })
        self.assertEqual(outlook_recurring_event.name, 'Updated from Outlook')

        # Remove token: organizer is no longer synced to Outlook
        self.organizer_user.microsoft_calendar_token = False

        # Any user should be able to edit a non-Outlook recurring event
        for user in [self.attendee_user, self.organizer_user]:
            recurring_event.with_user(user).with_context(dont_notify=False).write({
                'name': f'Changed by {user.name}',
                'recurrence_update': 'future_events',
            })
            self.assertEqual(recurring_event.name, f'Changed by {user.name}')

    def test_map_an_event_using_global_id(self):
        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": event_uid,
            "id": event_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[event_id]["_odoo_id"], self.simple_event.id)

    def test_map_an_event_using_instance_id(self):
        """
        Here, the Odoo event has an uid but the Outlook event has not.
        """
        # arrange
        event_id = self.simple_event.microsoft_id
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": False,
            "id": event_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[event_id]["_odoo_id"], self.simple_event.id)

    def test_map_an_event_without_uid_using_instance_id(self):
        """
        Here, the Odoo event has no uid but the Outlook event has one.
        """

        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        self.simple_event.ms_universal_event_id = False
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": event_uid,
            "id": event_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[event_id]["_odoo_id"], self.simple_event.id)
        self.assertEqual(self.simple_event.ms_universal_event_id, event_uid)

    def test_map_an_event_without_uid_using_instance_id_2(self):
        """
        Here, both Odoo event and Outlook event have no uid.
        """

        # arrange
        event_id = self.simple_event.microsoft_id
        self.simple_event.ms_universal_event_id = False
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": False,
            "id": event_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[event_id]["_odoo_id"], self.simple_event.id)
        self.assertEqual(self.simple_event.ms_universal_event_id, False)

    def test_map_a_recurrence_using_global_id(self):

        # arrange
        rec_id = self.recurrence.microsoft_id
        rec_uid = self.recurrence.ms_universal_event_id
        events = MicrosoftEvent([{
            "type": "seriesMaster",
            "_odoo_id": False,
            "iCalUId": rec_uid,
            "id": rec_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[rec_id]["_odoo_id"], self.recurrence.id)

    def test_map_a_recurrence_using_instance_id(self):

        # arrange
        rec_id = self.recurrence.microsoft_id
        events = MicrosoftEvent([{
            "type": "seriesMaster",
            "_odoo_id": False,
            "iCalUId": False,
            "id": rec_id,
        }])

        # act
        mapped = events._load_odoo_ids_from_db(self.env)

        # assert
        self.assertEqual(len(mapped._events), 1)
        self.assertEqual(mapped._events[rec_id]["_odoo_id"], self.recurrence.id)

    def test_try_to_map_mixed_of_single_events_and_recurrences(self):

        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        rec_id = self.recurrence.microsoft_id
        rec_uid = self.recurrence.ms_universal_event_id

        events = MicrosoftEvent([
            {
                "type": "seriesMaster",
                "_odoo_id": False,
                "iCalUId": rec_uid,
                "id": rec_id,
            },
            {
                "type": "singleInstance",
                "_odoo_id": False,
                "iCalUId": event_uid,
                "id": event_id,
            },
        ])

        # act & assert
        with self.assertRaises(TypeError):
            events._load_odoo_ids_from_db(self.env)

    def test_match_event_only(self):

        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": event_uid,
            "id": event_id,
        }])

        # act
        matched = events.match_with_odoo_events(self.env)

        # assert
        self.assertEqual(len(matched._events), 1)
        self.assertEqual(matched._events[event_id]["_odoo_id"], self.simple_event.id)

    def test_match_recurrence_only(self):

        # arrange
        rec_id = self.recurrence.microsoft_id
        rec_uid = self.recurrence.ms_universal_event_id
        events = MicrosoftEvent([{
            "type": "seriesMaster",
            "_odoo_id": False,
            "iCalUId": rec_uid,
            "id": rec_id,
        }])

        # act
        matched = events.match_with_odoo_events(self.env)

        # assert
        self.assertEqual(len(matched._events), 1)
        self.assertEqual(matched._events[rec_id]["_odoo_id"], self.recurrence.id)

    def test_match_not_typed_recurrence(self):
        """
        When a recurrence is deleted, Outlook returns the id of the deleted recurrence
        without the type of event, so it's not directly possible to know that it's a
        recurrence.
        """
        # arrange
        rec_id = self.recurrence.microsoft_id
        rec_uid = self.recurrence.ms_universal_event_id
        events = MicrosoftEvent([{
            "@removed": {
                "reason": "deleted",
            },
            "_odoo_id": False,
            "iCalUId": rec_uid,
            "id": rec_id,
        }])

        # act
        matched = events.match_with_odoo_events(self.env)

        # assert
        self.assertEqual(len(matched._events), 1)
        self.assertEqual(matched._events[rec_id]["_odoo_id"], self.recurrence.id)

    def test_match_mix_of_events_and_recurrences(self):

        # arrange
        event_id = self.simple_event.microsoft_id
        event_uid = self.simple_event.ms_universal_event_id
        rec_id = self.recurrence.microsoft_id
        rec_uid = self.recurrence.ms_universal_event_id

        events = MicrosoftEvent([
            {
                "type": "singleInstance",
                "_odoo_id": False,
                "iCalUId": event_uid,
                "id": event_id,
            },
            {
                "@removed": {
                    "reason": "deleted",
                },
                "_odoo_id": False,
                "iCalUId": rec_uid,
                "id": rec_id,
            }
        ])

        # act
        matched = events.match_with_odoo_events(self.env)

        # assert
        self.assertEqual(len(matched._events), 2)
        self.assertEqual(matched._events[event_id]["_odoo_id"], self.simple_event.id)
        self.assertEqual(matched._events[rec_id]["_odoo_id"], self.recurrence.id)

    def test_ignore_not_found_items(self):

        # arrange
        events = MicrosoftEvent([{
            "type": "singleInstance",
            "_odoo_id": False,
            "iCalUId": "UNKNOWN_EVENT",
            "id": "UNKNOWN_EVENT",
        }])

        # act
        matched = events.match_with_odoo_events(self.env)

        # assert
        self.assertEqual(len(matched._events), 0)

    def test_search_set_ms_universal_event_id(self):
        not_synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '=', False)])
        synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '!=', False)])
        self.assertIn(self.simple_event, synced_events)
        self.assertNotIn(self.simple_event, not_synced_events)

        self.simple_event.ms_universal_event_id = False
        not_synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '=', False)])
        synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '!=', False)])

        self.assertNotIn(self.simple_event, synced_events)
        self.assertIn(self.simple_event, not_synced_events)

    @patch_api
    def test_single_event_turned_recurrent_in_outlook_no_duplicate(self):
        """ Sync a single event, then turn it into a recurrence in Outlook. """

        master_id = 'AAAKROSMOZ0001=='
        master_uid = '040000008200E00074C5B7101A82E0080000000099VULKANIA00000000000000DEADBEEF'
        future = (datetime.now() + relativedelta(days=1)).isoformat()

        # arrange
        single = [{
            '@odata.type': '#microsoft.graph.event',
            '@odata.etag': 'W/"SINGLE"',
            'type': 'singleInstance',
            'subject': 'Bouftou',
            'isCancelled': False,
            'id': master_id,
            'iCalUId': master_uid,
            'start': {'dateTime': '2021-09-01T10:00:00.0000000', 'timeZone': 'UTC'},
            'end': {'dateTime': '2021-09-01T10:30:00.0000000', 'timeZone': 'UTC'},
            'location': {'displayName': ''},
        }]
        self.env['calendar.event']._sync_microsoft2odoo(MicrosoftEvent(single))
        odoo_single = self.env['calendar.event'].search([
            ('microsoft_id', '=', master_id),
            ('ms_universal_event_id', '=', master_uid),
        ])
        self.assertEqual(len(odoo_single), 1, "The single event should have been created")
        self.assertFalse(odoo_single.recurrence_id)

        # act
        recurrent = [
            {'@odata.type': '#microsoft.graph.event', '@odata.etag': 'W/"MASTER"', 'createdDateTime': '2021-09-01T07:03:49.1444085Z', 'lastModifiedDateTime': future, 'changeKey': 'MASTER', 'categories': [], 'originalStartTimeZone': 'UTC', 'originalEndTimeZone': 'UTC', 'iCalUId': master_uid, 'reminderMinutesBeforeStart': 15, 'isReminderOn': True, 'hasAttachments': False, 'subject': 'Bouftou', 'bodyPreview': '', 'importance': 'normal', 'sensitivity': 'normal', 'isAllDay': False, 'isCancelled': False, 'isOrganizer': True, 'responseRequested': True, 'seriesMasterId': None, 'showAs': 'busy', 'type': 'seriesMaster', 'AllowNewTimeProposals': True, 'IsDraft': False, 'id': master_id, 'responseStatus': {'response': 'organizer', 'time': '0001-01-01T00:00:00Z'}, 'body': {'contentType': 'html', 'content': ''}, 'start': {'dateTime': '2021-09-01T10:00:00.0000000', 'timeZone': 'UTC'}, 'end': {'dateTime': '2021-09-01T10:30:00.0000000', 'timeZone': 'UTC'}, 'location': {'displayName': '', 'locationType': 'default', 'uniqueIdType': 'unknown', 'address': {}, 'coordinates': {}}, 'locations': [], 'recurrence': {'pattern': {'type': 'daily', 'interval': 1, 'month': 0, 'dayOfMonth': 0, 'firstDayOfWeek': 'sunday', 'index': 'first'}, 'range': {'type': 'endDate', 'startDate': '2021-09-01', 'endDate': '2021-09-03', 'recurrenceTimeZone': 'UTC', 'numberOfOccurrences': 0}}, 'attendees': [], 'organizer': {'emailAddress': {'name': 'Kerubim', 'address': 'kerubim@test.com'}}},
            {'@odata.type': '#microsoft.graph.event', '@odata.etag': 'W/"OCC1"', 'seriesMasterId': master_id, 'type': 'occurrence', 'id': 'OCC0001', 'start': {'dateTime': '2021-09-01T10:00:00.0000000', 'timeZone': 'UTC'}, 'end': {'dateTime': '2021-09-01T10:30:00.0000000', 'timeZone': 'UTC'}},
            {'@odata.type': '#microsoft.graph.event', '@odata.etag': 'W/"OCC2"', 'seriesMasterId': master_id, 'type': 'occurrence', 'id': 'OCC0002', 'start': {'dateTime': '2021-09-02T10:00:00.0000000', 'timeZone': 'UTC'}, 'end': {'dateTime': '2021-09-02T10:30:00.0000000', 'timeZone': 'UTC'}},
            {'@odata.type': '#microsoft.graph.event', '@odata.etag': 'W/"OCC3"', 'seriesMasterId': master_id, 'type': 'occurrence', 'id': 'OCC0003', 'start': {'dateTime': '2021-09-03T10:00:00.0000000', 'timeZone': 'UTC'}, 'end': {'dateTime': '2021-09-03T10:30:00.0000000', 'timeZone': 'UTC'}},
        ]
        microsoft_delete_calls = []

        def track_microsoft_delete(*args, **kwargs):
            microsoft_delete_calls.append((args, kwargs))

        with patch.object(MicrosoftSync, '_microsoft_delete', track_microsoft_delete):
            self.env['calendar.event']._sync_microsoft2odoo(MicrosoftEvent(recurrent))

        # assert
        self.assertFalse(microsoft_delete_calls, "It should not delete the event from Outlook")
        recurrence = self.env['calendar.recurrence'].search([
            ('microsoft_id', '=', master_id),
            ('ms_universal_event_id', '=', master_uid),
        ])
        self.assertTrue(recurrence, "It should have created a recurrence")
        self.assertEqual(len(recurrence.calendar_event_ids), 3, "It should have created 3 occurrences")

        # The former single event must not survive as an orphan duplicate.
        leftover_single = self.env['calendar.event'].search([
            ('ms_universal_event_id', '=', master_uid),
            ('recurrence_id', '=', False),
        ])
        self.assertFalse(
            leftover_single,
            "The single event turned recurrent must not remain as a duplicate next to the recurrence",
        )
        first_slot = self.env['calendar.event'].search([('start', '=', datetime(2021, 9, 1, 10, 0))])
        self.assertEqual(len(first_slot), 1, "Only the recurrence occurrence should remain on the first slot")

    def test_microsoft_event_readonly(self):
        event = MicrosoftEvent()
        with self.assertRaises(TypeError):
            event._events['foo'] = 'bar'
        with self.assertRaises(AttributeError):
            event._events.update({'foo': 'bar'})
        with self.assertRaises(TypeError):
            dict.update(event._events, {'foo': 'bar'})

    def test_performance_check(self):
        # Test what happens when microsoft returns a lot of data
        # This test does not aim to check what we do with the data but it ensure that we are able to process it.
        # Other tests take care of how we update odoo records with the api result.

        start_date = datetime(2023, 9, 25, 17, 25)
        record_count = 10000
        single_event_data = [{
            '@odata.type': '#microsoft.graph.event',
            '@odata.etag': f'W/"AAAAAA{x}"',
            'type': 'singleInstance',
            'createdDateTime': (start_date + relativedelta(minutes=x)).isoformat(),
            'lastModifiedDateTime': (datetime.now().astimezone(UTC) + relativedelta(days=3)).isoformat(),
            'changeKey': f'ZS2uEVAVyU6BMZ3m6cH{x}mtgAADI/Dig==',
            'categories': [],
            'originalStartTimeZone': 'Romance Standard Time',
            'originalEndTimeZone': 'Romance Standard Time',
            'id': f'AA{x}',
            'subject': f"Subject of {x}",
            'bodyPreview': f"Body of {x}",
            'start': {'dateTime': (start_date + relativedelta(minutes=x)).isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': (start_date + relativedelta(minutes=x)).isoformat(), 'timeZone': 'UTC'},
            'isOrganizer': True,
            'organizer': {'emailAddress': {'name': f'outlook_{x}@outlook.com', 'address': f'outlook_{x}@outlook.com'}},
        } for x in range(record_count)]

        events = MicrosoftEvent(single_event_data)
        mapped = events._load_odoo_ids_from_db(self.env)
        self.assertFalse(mapped, "No odoo record should correspond to the microsoft values")

        recurring_event_data = [{
            '@odata.type': '#microsoft.graph.event',
            '@odata.etag': f'W/"{x}IaZKQ=="',
            'createdDateTime': (start_date + relativedelta(minutes=(2*x))).isoformat(),
            'lastModifiedDateTime': (datetime.now().astimezone(UTC) + relativedelta(days=3)).isoformat(),
            'changeKey': 'ZS2uEVAVyU6BMZ3m6cHmtgAADIaZKQ==',
            'categories': [],
            'originalStartTimeZone': 'Romance Standard Time',
            'originalEndTimeZone': 'Romance Standard Time',
            'iCalUId': f'XX{x}',
            'id': f'AAA{x}',
            'reminderMinutesBeforeStart': 15,
            'isReminderOn': True,
            'hasAttachments': False,
            'subject': f'My recurrent event {x}',
            'bodyPreview': '', 'importance':
            'normal', 'sensitivity': 'normal',
            'isAllDay': False, 'isCancelled': False,
            'isOrganizer': True, 'IsRoomRequested': False,
            'AutoRoomBookingStatus': 'None',
            'responseRequested': True,
            'seriesMasterId': None,
            'showAs': 'busy',
            'type': 'seriesMaster',
            'webLink': f'https://outlook.live.com/owa/?itemid={x}&exvsurl=1&path=/calendar/item',
            'onlineMeetingUrl': None,
            'isOnlineMeeting': False,
            'onlineMeetingProvider': 'unknown', 'AllowNewTimeProposals': True,
            'IsDraft': False,
            'responseStatus': {'response': 'organizer', 'time': '0001-01-01T00:00:00Z'},
            'body': {'contentType': 'html', 'content': ''},
            'start': {'dateTime': '2020-05-03T14:30:00.0000000', 'timeZone': 'UTC'},
            'end': {'dateTime': '2020-05-03T16:00:00.0000000', 'timeZone': 'UTC'},
            'location': {'displayName': '',
                         'locationType': 'default',
                         'uniqueIdType': 'unknown',
                         'address': {},
                         'coordinates': {}},
            'locations': [],
            'recurrence': {'pattern':
                               {'type': 'daily',
                                'interval': 1,
                                'month': 0,
                                'dayOfMonth': 0,
                                'firstDayOfWeek': 'sunday',
                                'index': 'first'},
                                'range': {'type': 'endDate',
                                          'startDate': '2020-05-03',
                                          'endDate': '2020-05-05',
                                          'recurrenceTimeZone': 'Romance Standard Time',
                                          'numberOfOccurrences': 0}
                           },
            'attendees': [],
            'organizer': {'emailAddress': {'name': f'outlook_{x}@outlook.com',
                                           'address': f'outlook_{x}@outlook.com'}}
            } for x in range(record_count)]

        recurrences = MicrosoftEvent(recurring_event_data)
        mapped = recurrences._load_odoo_ids_from_db(self.env)
        self.assertFalse(mapped, "No odoo record should correspond to the microsoft values")
