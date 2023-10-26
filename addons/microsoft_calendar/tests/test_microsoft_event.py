from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.tests.common import TestCommon, patch_api

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
