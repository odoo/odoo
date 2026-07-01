# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.addons.mail.tests.common import MailCase
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token


@patch.object(User, '_get_microsoft_calendar_token', mock_get_token)
class TestSyncOdoo2MicrosoftMail(TestCommon, MailCase):

    @freeze_time("2021-09-22")
    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_no_invitation_email_on_recurrent_exception_from_outlook_sync(self, mock_get_events):
        """Invitation emails must not be sent when syncing a recurring event with exception occurrences from Outlook."""
        organizer = self.organizer_user
        organizer_payload = {
            'emailAddress': {'address': organizer.email, 'name': organizer.display_name},
        }

        attendee = self.attendee_user
        attendees_payload = [
            {
                'type': 'required',
                'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                'emailAddress': {'name': attendee.display_name, 'address': attendee.email},
            },
        ]

        common_fields = {
            'body': {'content': '', 'contentType': 'text'},
            'isAllDay': False, 'isCancelled': False, 'isOnlineMeeting': False,
            'isOrganizer': True, 'isReminderOn': False,
            'location': {'displayName': ''},
            'organizer': organizer_payload,
            'reminderMinutesBeforeStart': 0, 'responseRequested': True,
            'responseStatus': {'response': 'organizer', 'time': '0001-01-01T00:00:00Z'},
            'sensitivity': 'normal', 'showAs': 'busy',
            'attendees': attendees_payload,
        }

        series_start = datetime(2021, 9, 23, 13, 0)
        series_stop = datetime(2021, 9, 23, 14, 0)
        series_master = {
            **common_fields,
            'type': 'seriesMaster',
            'id': 'SERIES_MASTER_ID',
            'iCalUId': 'SERIES_MASTER_ICALUID',
            'seriesMasterId': None,
            'subject': 'Amakna',
            'start': {'dateTime': series_start.strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
            'end': {'dateTime': series_stop.strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
            'recurrence': {
                'pattern': {
                    'type': 'daily', 'interval': 14,
                    'dayOfMonth': 0, 'firstDayOfWeek': 'sunday', 'index': 'first', 'month': 0,
                },
                'range': {
                    'type': 'endDate',
                    'startDate': series_start.strftime('%Y-%m-%d'),
                    'endDate': (series_start + timedelta(days=42)).strftime('%Y-%m-%d'),
                    'numberOfOccurrences': 0, 'recurrenceTimeZone': 'UTC',
                },
            },
        }

        occ_start = series_start + timedelta(days=14)
        regular_occurrence = {
            **common_fields,
            'type': 'occurrence',
            'id': 'OCCURRENCE_ID_1',
            'iCalUId': 'OCCURRENCE_ICALUID_1',
            'seriesMasterId': 'SERIES_MASTER_ID',
            'subject': 'Amakna',
            'recurrence': None,
            'start': {'dateTime': occ_start.strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
            'end': {'dateTime': (occ_start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
        }

        exc_start = series_start + timedelta(days=4)
        exception_occurrence = {
            **common_fields,
            'type': 'exception',
            'id': 'EXCEPTION_ID_1',
            'iCalUId': 'EXCEPTION_ICALUID_1',
            'seriesMasterId': 'SERIES_MASTER_ID',
            'subject': 'Amakna',
            'recurrence': None,
            'start': {'dateTime': exc_start.strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
            'end': {'dateTime': (exc_start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.0000000'), 'timeZone': 'UTC'},
        }

        mock_get_events.return_value = (
            MicrosoftEvent([series_master, regular_occurrence, exception_occurrence]),
            None,
        )

        with self.mock_mail_gateway():
            organizer.with_user(organizer).sudo()._sync_microsoft_calendar()

        events = self.env['calendar.event'].search([('name', '=', 'Amakna')])
        self.assertTrue(all(e.microsoft_id for e in events), "All synced events must have microsoft_id set")
        self.assertNotSentEmail()
