# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestUnsyncedAttendees(TransactionCase):
    """ Check the warning banner listing attendees not synced with Google. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organizer = cls._create_user("organizer", synced=True)
        cls.synced = cls._create_user("synced", synced=True)
        cls.unsynced = cls._create_user("unsynced", synced=False)
        cls.external = cls.env["res.partner"].create({
            "name": "External Guest",
            "email": "guest@example.com",
        })

    @classmethod
    def _create_user(cls, login, synced):
        user = cls.env["res.users"].create({
            "name": login,
            "login": login,
            "email": f"{login}@example.com",
        })
        if synced:
            user.res_users_settings_id.write({
                "google_calendar_rtoken": f"{login}_rtoken",
                "google_synchronization_stopped": False,
            })
        return user

    def _create_event(self, partners):
        return self.env["calendar.event"].with_user(self.organizer).create({
            "name": "meeting",
            "start": datetime(2021, 9, 22, 10, 0, 0),
            "stop": datetime(2021, 9, 22, 11, 0, 0),
            "partner_ids": [(6, 0, partners.ids)],
        })

    def test_unsynced_partner_listed(self):
        """ An attendee whose user has no active Google sync is flagged. """
        event = self._create_event(
            self.organizer.partner_id + self.unsynced.partner_id
        )
        self.assertEqual(
            event.google_unsynced_partner_ids,
            self.unsynced.partner_id,
            "Only the attendee without active Google sync must be flagged.",
        )

    def test_synced_attendee_not_listed(self):
        """ Attendees with an active Google sync are not flagged. """
        event = self._create_event(
            self.organizer.partner_id + self.synced.partner_id
        )
        self.assertFalse(
            event.google_unsynced_partner_ids,
            "No banner when every attendee is synced with Google.",
        )

    def test_external_partner_not_listed(self):
        """ Attendees that are not Odoo users (external) are never flagged. """
        event = self._create_event(self.organizer.partner_id + self.external)
        self.assertFalse(
            event.google_unsynced_partner_ids,
            "External attendees without an Odoo user must not be flagged.",
        )
