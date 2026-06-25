# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.microsoft_calendar.tests.common import TestCommon


@tagged("post_install", "-at_install")
class TestUnsyncedAttendees(TestCommon):
    """ Check the warning banner listing attendees not synced with Outlook. """

    def _set_sync(self, user, active):
        user.sudo().microsoft_calendar_rtoken = "a_token" if active else False
        user.sudo().microsoft_synchronization_stopped = not active

    def test_unsynced_partner_listed(self):
        """ An attendee whose user has no active Outlook sync is flagged. """
        self._set_sync(self.organizer_user, True)
        self._set_sync(self.attendee_user, False)

        event = self.env["calendar.event"].with_user(self.organizer_user).create({
            "name": "meeting",
            "start": self.start_date,
            "stop": self.end_date,
            "partner_ids": [
                (4, self.organizer_user.partner_id.id),
                (4, self.attendee_user.partner_id.id),
            ],
        })
        self.assertEqual(
            event.microsoft_unsynced_partner_ids,
            self.attendee_user.partner_id,
            "Only the attendee without active Outlook sync must be flagged.",
        )

    def test_synced_attendee_not_listed(self):
        """ Attendees with an active Outlook sync are not flagged. """
        self._set_sync(self.organizer_user, True)
        self._set_sync(self.attendee_user, True)

        event = self.env["calendar.event"].with_user(self.organizer_user).create({
            "name": "meeting",
            "start": self.start_date,
            "stop": self.end_date,
            "partner_ids": [
                (4, self.organizer_user.partner_id.id),
                (4, self.attendee_user.partner_id.id),
            ],
        })
        self.assertFalse(
            event.microsoft_unsynced_partner_ids,
            "No banner when every attendee is synced with Outlook.",
        )

    def test_external_partner_not_listed(self):
        """ Attendees that are not Odoo users (external) are never flagged. """
        self._set_sync(self.organizer_user, True)
        external = self.env["res.partner"].create({
            "name": "External Guest",
            "email": "guest@example.com",
        })

        event = self.env["calendar.event"].with_user(self.organizer_user).create({
            "name": "meeting",
            "start": self.start_date,
            "stop": self.end_date,
            "partner_ids": [
                (4, self.organizer_user.partner_id.id),
                (4, external.id),
            ],
        })
        self.assertFalse(
            event.microsoft_unsynced_partner_ids,
            "External attendees without an Odoo user must not be flagged.",
        )
