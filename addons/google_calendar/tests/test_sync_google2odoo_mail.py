# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime
from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleEvent
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged


@tagged('google2odoo')
@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncGoogle2OdooMail(TestSyncGoogle, MailCommon):
    """ Events coming from Google must never trigger Odoo-side attendee
    invitation emails: Google already notifies the attendees itself. Before the
    fix, a Google->Odoo sync that added an attendee re-sent an invitation (and,
    for a recurrence, one per occurrence), spamming attendees. """

    @property
    def now(self):
        return pytz.utc.localize(datetime.now()).isoformat()

    def sync(self, events):
        events.clear_type_ambiguity(self.env)
        google_recurrence = events.filter(GoogleEvent.is_recurrence)
        self.env['calendar.recurrence']._sync_google2odoo(google_recurrence)
        self.env['calendar.event']._sync_google2odoo(events - google_recurrence)

    @patch_api
    def test_sync_from_google_does_not_send_invitations(self):
        google_id = 'spammy_event_001'
        event_values = {
            'id': google_id,
            'summary': 'Synced meeting',
            'start': {'dateTime': '2027-01-06T09:00:00+00:00', 'timeZone': 'UTC'},
            'end': {'dateTime': '2027-01-06T10:00:00+00:00', 'timeZone': 'UTC'},
            'reminders': {'useDefault': False},
            'organizer': {'email': self.organizer_user.email},
            'updated': self.now,
        }

        # 1. Initial sync from Google: event with only the organizer as attendee.
        self.sync(GoogleEvent([dict(event_values, attendees=[
            {'email': self.organizer_user.email, 'responseStatus': 'accepted'},
        ])]))
        event = self.env['calendar.event'].search([('google_id', '=', google_id)])
        self.assertTrue(event, "initial sync should have created the event")

        # 2. Google update adds a new attendee. This is the write that, before the
        #    fix, triggered calendar.event._notify_attendees for the new partner
        #    because the sync only set `dont_notify` (which guards alarms), not
        #    `skip_attendee_notification` (which guards invitations).
        with self.mock_mail_gateway():
            self.sync(GoogleEvent([dict(event_values, updated=self.now, attendees=[
                {'email': self.organizer_user.email, 'responseStatus': 'accepted'},
                {'email': self.attendee_user.email, 'responseStatus': 'needsAction'},
            ])]))

        self.assertIn(self.attendee_user.partner_id, event.partner_ids,
                      "the attendee must have been synced from Google")
        self.assertNotSentEmail(self.attendee_user.partner_id)
