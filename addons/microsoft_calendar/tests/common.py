import pytz
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests.common import HttpCase

from odoo.addons.microsoft_calendar.models.microsoft_sync import MicrosoftSync
from odoo.addons.microsoft_calendar.utils.event_id_storage import combine_ids

def mock_get_token(user):
    return f"TOKEN_FOR_USER_{user.id}"

def _modified_date_in_the_future(event):
    """
    Add some seconds to the event write date to be sure to have a last modified date
    in the future
    """
    return (event.write_date + timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

def patch_api(func):
    @patch.object(MicrosoftSync, '_microsoft_insert', MagicMock())
    @patch.object(MicrosoftSync, '_microsoft_delete', MagicMock())
    @patch.object(MicrosoftSync, '_microsoft_patch', MagicMock())
    def patched(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return patched

# By inheriting from TransactionCase, postcommit hooks (so methods tagged with `@after_commit` in MicrosoftSync),
# are not called because no commit is done.
# To be able to manually call these postcommit hooks, we need to inherit from HttpCase.
# Note: as postcommit hooks are called separately, do not forget to invalidate cache for records read during the test.
class TestCommon(HttpCase):

    @patch_api
    def setUp(self):
        super(TestCommon, self).setUp()

        # prepare users
        self.organizer_user = self.env["res.users"].search([("name", "=", "Mike Organizer")])
        if not self.organizer_user:
            partner = self.env['res.partner'].create({'name': 'Mike Organizer', 'email': 'mike@organizer.com'})
            self.organizer_user = self.env['res.users'].create({
                'name': 'Mike Organizer',
                'login': 'mike@organizer.com',
                'partner_id': partner.id,
            })

        self.attendee_user = self.env["res.users"].search([("name", "=", "John Attendee")])
        if not self.attendee_user:
            partner = self.env['res.partner'].create({'name': 'John Attendee', 'email': 'john@attendee.com'})
            self.attendee_user = self.env['res.users'].create({
                'name': 'John Attendee',
                'login': 'john@attendee.com',
                'partner_id': partner.id,
            })

        # -----------------------------------------------------------------------------------------
        # To create Odoo events
        # -----------------------------------------------------------------------------------------
        self.start_date = datetime(2021, 9, 22, 10, 0, 0, 0)
        self.end_date = datetime(2021, 9, 22, 11, 0, 0, 0)
        self.recurrent_event_interval = 2
        self.recurrent_events_count = 7
        self.recurrence_end_date = self.end_date + timedelta(
            days=self.recurrent_event_interval * self.recurrent_events_count
        )

        # simple event values to create a Odoo event
        self.simple_event_values = {
            "name": "simple_event",
            "description": "my simple event",
            "active": True,
            "start": self.start_date,
            "stop": self.end_date,
            "partner_ids": [(4, self.organizer_user.partner_id.id), (4, self.attendee_user.partner_id.id)],
        }
        self.recurrent_event_values = {
            'name': 'recurring_event',
            'description': 'a recurring event',
            "partner_ids": [(4, self.attendee_user.partner_id.id)],
            'recurrency': True,
            'follow_recurrence': True,
            'start': self.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            'stop': self.end_date.strftime("%Y-%m-%d %H:%M:%S"),
            'event_tz': 'Europe/London',
            'recurrence_update': 'self_only',
            'rrule_type': 'daily',
            'interval': self.recurrent_event_interval,
            'count': self.recurrent_events_count,
            'end_type': 'count',
            'duration': 1,
            'byday': '-1',
            'day': 22,
            'we': True,
            'weekday': 'WE'
        }

        # -----------------------------------------------------------------------------------------
        # Expected values for Odoo events converted to Outlook events (to be posted through API)
        # -----------------------------------------------------------------------------------------

        # simple event values converted in the Outlook format to be posted through the API
        self.simple_event_ms_values = {
            "subject": self.simple_event_values["name"],
            "body": {
                'content': self.simple_event_values["description"],
                'contentType': "text",
            },
            "start": {
                'dateTime': pytz.utc.localize(self.simple_event_values["start"]).isoformat(),
                'timeZone': 'Europe/London'
            },
            "end": {
                'dateTime': pytz.utc.localize(self.simple_event_values["stop"]).isoformat(),
                'timeZone': 'Europe/London'
            },
            "isAllDay": False,
            "organizer": {
                'emailAddress': {
                    'address': self.organizer_user.email,
                    'name': self.organizer_user.display_name,
                }
            },
            "isOrganizer": True,
            "sensitivity": "normal",
            "showAs": "busy",
            "attendees": [
                {
                    'emailAddress': {
                        'address': self.attendee_user.email,
                        'name': self.attendee_user.display_name
                    },
                    'status': {'response': "notresponded"}
                }
            ],
            "isReminderOn": False,
            "location": {'displayName': ''},
            "reminderMinutesBeforeStart": 0,
        }

        self.recurrent_event_ms_values = {
            'subject': self.recurrent_event_values["name"],
            "body": {
                'content': self.recurrent_event_values["description"],
                'contentType': "text",
            },
            'start': {
                'dateTime': self.start_date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                'timeZone': 'Europe/London'
            },
            'end': {
                'dateTime': self.end_date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                'timeZone': 'Europe/London'
            },
            'isAllDay': False,
            'isOrganizer': True,
            'isReminderOn': False,
            'reminderMinutesBeforeStart': 0,
            'sensitivity': 'normal',
            'showAs': 'busy',
            'type': 'seriesMaster',
            "attendees": [
                {
                    'emailAddress': {
                        'address': self.attendee_user.email,
                        'name': self.attendee_user.display_name
                    },
                    'status': {'response': "notresponded"}
                }
            ],
            'location': {'displayName': ''},
            'organizer': {
                'emailAddress': {
                    'address': self.organizer_user.email,
                    'name': self.organizer_user.display_name,
                },
            },
            'recurrence': {
                'pattern': {'dayOfMonth': 22, 'interval': self.recurrent_event_interval, 'type': 'daily'},
                'range': {
                    'numberOfOccurrences': self.recurrent_events_count,
                    'startDate': self.start_date.strftime("%Y-%m-%d"),
                    'type': 'numbered'
                },
            },
        }

        # -----------------------------------------------------------------------------------------
        # Events coming from Outlook (so from the API)
        # -----------------------------------------------------------------------------------------

        self.simple_event_from_outlook_organizer = {
            'type': 'singleInstance',
            'seriesMasterId': None,
            'id': '123',
            'iCalUId': '456',
            'subject': 'simple_event',
            'body': {
                'content': "my simple event",
                'contentType': "text",
            },
            'start': {'dateTime': self.start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            'end': {'dateTime': self.end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            'attendees': [{
                'type': 'required',
                'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                'emailAddress': {'name': self.attendee_user.display_name, 'address': self.attendee_user.email}
            }],
            'isAllDay': False,
            'isCancelled': False,
            'sensitivity': 'normal',
            'showAs': 'busy',
            'isOnlineMeeting': False,
            'onlineMeetingUrl': None,
            'isOrganizer': True,
            'isReminderOn': True,
            'location': {'displayName': ''},
            'organizer': {
                'emailAddress': {'address': self.organizer_user.email, 'name': self.organizer_user.display_name},
            },
            'reminderMinutesBeforeStart': 15,
            'responseRequested': True,
            'responseStatus': {
                'response': 'organizer',
                'time': '0001-01-01T00:00:00Z',
            },
        }

        self.simple_event_from_outlook_attendee = self.simple_event_from_outlook_organizer
        self.simple_event_from_outlook_attendee.update(isOrganizer=False)

        # -----------------------------------------------------------------------------------------
        # Expected values for Outlook events converted to Odoo events
        # -----------------------------------------------------------------------------------------

        self.expected_odoo_event_from_outlook = {
            "name": "simple_event",
            "description": "my simple event",
            "active": True,
            "start": self.start_date,
            "stop": self.end_date,
            "user_id": self.organizer_user,
            "microsoft_id": combine_ids("123", "456"),
            "partner_ids": [self.organizer_user.partner_id.id, self.attendee_user.partner_id.id],
        }
        self.expected_odoo_recurrency_from_outlook = {
            'active': True,
            'byday': '1',
            'count': 0,
            'day': 0,
            'display_name': "Every %s Days, until %s" % (
                self.recurrent_event_interval, self.recurrence_end_date.strftime("%Y-%m-%d")
            ),
            'dtstart': self.start_date,
            'end_type': 'end_date',
            'event_tz': False,
            'fr': False,
            'interval': self.recurrent_event_interval,
            'month_by': 'date',
            'microsoft_id': combine_ids('REC123', 'REC456'),
            'name': "Every %s Days, until %s" % (
                self.recurrent_event_interval, self.recurrence_end_date.strftime("%Y-%m-%d")
            ),
            'need_sync_m': False,
            'rrule': 'DTSTART:%s\nRRULE:FREQ=DAILY;INTERVAL=%s;UNTIL=%s' % (
                self.start_date.strftime("%Y%m%dT%H%M%S"),
                self.recurrent_event_interval,
                self.recurrence_end_date.strftime("%Y%m%dT235959"),
            ),
            'rrule_type': 'daily',
            'until': self.recurrence_end_date.date(),
            'weekday': False,
        }

        self.recurrent_event_from_outlook_organizer = [{
            'attendees': [{
                'emailAddress': {'address': self.attendee_user.email, 'name': self.attendee_user.display_name},
                'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                'type': 'required'
            }],
            'body': {
                'content': "my recurrent event",
                'contentType': "text",
            },
            'start': {'dateTime': self.start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            'end': {'dateTime': self.end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            'id': 'REC123',
            'iCalUId': 'REC456',
            'isAllDay': False,
            'isCancelled': False,
            'isOnlineMeeting': False,
            'isOrganizer': True,
            'isReminderOn': True,
            'location': {'displayName': ''},
            'organizer': {'emailAddress': {
                'address': self.organizer_user.email, 'name': self.organizer_user.display_name}
            },
            'recurrence': {
                'pattern': {
                    'dayOfMonth': 0,
                    'firstDayOfWeek': 'sunday',
                    'index': 'first',
                    'interval': self.recurrent_event_interval,
                    'month': 0,
                    'type': 'daily'
                },
                'range': {
                    'startDate': self.start_date.strftime("%Y-%m-%d"),
                    'endDate': self.recurrence_end_date.strftime("%Y-%m-%d"),
                    'numberOfOccurrences': 0,
                    'recurrenceTimeZone': 'Romance Standard Time',
                    'type': 'endDate'
                }
            },
            'reminderMinutesBeforeStart': 15,
            'responseRequested': True,
            'responseStatus': {'response': 'organizer', 'time': '0001-01-01T00:00:00Z'},
            'sensitivity': 'normal',
            'seriesMasterId': None,
            'showAs': 'busy',
            'subject': "recurrent event",
            'type': 'seriesMaster',
        }]
        self.recurrent_event_from_outlook_organizer += [
            {
                'attendees': [{
                    'emailAddress': {'address': self.attendee_user.email, 'name': self.attendee_user.display_name},
                    'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                    'type': 'required'
                }],
                'body': {
                    'content': "my recurrent event",
                    'contentType': "text",
                },
                'start': {
                    'dateTime': (
                        self.start_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': (
                        self.end_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                'id': f'REC123_EVENT_{i+1}',
                'iCalUId': f'REC456_EVENT_{i+1}',
                'seriesMasterId': 'REC123',
                'isAllDay': False,
                'isCancelled': False,
                'isOnlineMeeting': False,
                'isOrganizer': True,
                'isReminderOn': True,
                'location': {'displayName': ''},
                'organizer': {
                    'emailAddress': {'address': self.organizer_user.email, 'name': self.organizer_user.display_name}
                },
                'recurrence': None,
                'reminderMinutesBeforeStart': 15,
                'responseRequested': True,
                'responseStatus': {'response': 'organizer', 'time': '0001-01-01T00:00:00Z'},
                'sensitivity': 'normal',
                'showAs': 'busy',
                'subject': "recurrent event",
                'type': 'occurrence',
            }
            for i in range(self.recurrent_events_count)
        ]
        self.recurrent_event_from_outlook_attendee = [
            dict(
                d,
                isOrganizer=False,
                attendees=[
                    {
                        'emailAddress': {'address': self.organizer_user.email, 'name': self.organizer_user.display_name},
                        'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                        'type': 'required'
                    },
                    {
                        'emailAddress': {'address': self.attendee_user.email, 'name': self.attendee_user.display_name},
                        'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                        'type': 'required'
                    },
                ]
            )
            for d in self.recurrent_event_from_outlook_organizer
        ]

        self.expected_odoo_recurrency_events_from_outlook = [
            {
                "name": "recurrent event",
                "user_id": self.organizer_user,
                "partner_ids": [self.organizer_user.partner_id.id, self.attendee_user.partner_id.id],
                "start": self.start_date + timedelta(days=i * self.recurrent_event_interval),
                "stop": self.end_date + timedelta(days=i * self.recurrent_event_interval),
                "until": self.recurrence_end_date.date(),
                "microsoft_recurrence_master_id": "REC123",
                'microsoft_id': combine_ids(f"REC123_EVENT_{i+1}", f"REC456_EVENT_{i+1}"),
                "recurrency": True,
                "follow_recurrence": True,
                "active": True,
            }
            for i in range(self.recurrent_events_count)
        ]
        self.env.cr.postcommit.clear()

    def create_events_for_tests(self):
        """
        Create some events for test purpose
        """

        # ---- create some events that will be updated during tests -----

        # a simple event
        self.simple_event = self.env["calendar.event"].search([("name", "=", "simple_event")])
        if not self.simple_event:
            self.simple_event = self.env["calendar.event"].with_user(self.organizer_user).create(
                dict(
                    self.simple_event_values,
                    microsoft_id=combine_ids("123", "456"),
                )
            )

        # a group of events
        self.several_events = self.env["calendar.event"].search([("name", "like", "event%")])
        if not self.several_events:
            self.several_events = self.env["calendar.event"].with_user(self.organizer_user).create([
                dict(
                    self.simple_event_values,
                    name=f"event{i}",
                    microsoft_id=combine_ids(f"e{i}", f"u{i}"),
                )
                for i in range(1, 4)
            ])

        # a recurrent event with 7 occurrences
        self.recurrent_base_event = self.env["calendar.event"].search(
            [("name", "=", "recurrent_event")],
            order="id",
            limit=1,
        )
        already_created = self.recurrent_base_event

        if not already_created:
            self.recurrent_base_event = self.env["calendar.event"].with_user(self.organizer_user).create(
                self.recurrent_event_values
            )
        self.recurrence = self.env["calendar.recurrence"].search([("base_event_id", "=", self.recurrent_base_event.id)])

        # set ids set by Outlook
        if not already_created:
            self.recurrence.write({
                "microsoft_id": combine_ids("REC123", "REC456"),
            })
            for i, e in enumerate(self.recurrence.calendar_event_ids.sorted(key=lambda r: r.start)):
                e.write({
                    "microsoft_id": combine_ids(f"REC123_EVENT_{i+1}", f"REC456_EVENT_{i+1}"),
                    "microsoft_recurrence_master_id": "REC123",
                })
            self.recurrence.invalidate_cache()
            self.recurrence.calendar_event_ids.invalidate_cache()

        self.recurrent_events = self.recurrence.calendar_event_ids.sorted(key=lambda r: r.start)
        self.recurrent_events_count = len(self.recurrent_events)

    def assert_odoo_event(self, odoo_event, expected_values):
        """
        Assert that an Odoo event has the same values than in the expected_values dictionary,
        for the keys present in expected_values.
        """
        self.assertTrue(expected_values)

        odoo_event_values = odoo_event.read(list(expected_values.keys()))[0]
        for k, v in expected_values.items():
            if k in ("user_id", "recurrence_id"):
                v = (v.id, v.name) if v else False

            if isinstance(v, list):
                self.assertListEqual(sorted(v), sorted(odoo_event_values.get(k)), msg=f"'{k}' mismatch")
            else:
                self.assertEqual(v, odoo_event_values.get(k), msg=f"'{k}' mismatch")

    def assert_odoo_recurrence(self, odoo_recurrence, expected_values):
        """
        Assert that an Odoo recurrence has the same values than in the expected_values dictionary,
        for the keys present in expected_values.
        """
        odoo_recurrence_values = odoo_recurrence.read(list(expected_values.keys()))[0]

        for k, v in expected_values.items():
            self.assertEqual(v, odoo_recurrence_values.get(k), msg=f"'{k}' mismatch")

    def assert_dict_equal(self, dict1, dict2):

        # check missing keys
        keys = set(dict1.keys()) ^ set(dict2.keys())
        self.assertFalse(keys, msg="Following keys are not in both dicts: %s" % ", ".join(keys))

        # compare key by key
        for k, v in dict1.items():
            self.assertEqual(v, dict2.get(k), f"'{k}' mismatch")

    def call_post_commit_hooks(self):
        """
        manually calls postcommit hooks defined with the decorator @after_commit
        """

        # need to manually handle post-commit hooks calls as `self.env.cr.postcommit.run()` clean
        # the queue at the end of the first post-commit hook call ...
        funcs = self.env.cr.postcommit._funcs.copy()
        while funcs:
            func = funcs.popleft()
            func()
