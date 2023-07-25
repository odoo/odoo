from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.tests.common import TestCommon, patch_api

class TestMicrosoftEvent(TestCommon):

    @patch_api
    def setUp(self):
        super().setUp()
        self.create_events_for_tests()

    def test_already_mapped_events(self):

        # arrange
        event_id = self.simple_event.ms_organizer_event_id
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

    def test_map_an_event_using_global_id(self):

        # arrange
        event_id = self.simple_event.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
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
        rec_id = self.recurrence.ms_organizer_event_id
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
        rec_id = self.recurrence.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
        event_uid = self.simple_event.ms_universal_event_id
        rec_id = self.recurrence.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
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
        rec_id = self.recurrence.ms_organizer_event_id
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
        rec_id = self.recurrence.ms_organizer_event_id
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
        event_id = self.simple_event.ms_organizer_event_id
        event_uid = self.simple_event.ms_universal_event_id
        rec_id = self.recurrence.ms_organizer_event_id
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

        self.simple_event.ms_universal_event_id = ''
        not_synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '=', False)])
        synced_events = self.env['calendar.event'].search([('ms_universal_event_id', '!=', False)])

        self.assertNotIn(self.simple_event, synced_events)
        self.assertIn(self.simple_event, not_synced_events)
