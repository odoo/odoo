# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCalendarController(HttpCase):
    def setUp(self):
        super().setUp()
        self.user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", tz="UTC")
        self.other_user = new_test_user(self.env, "test_user_2", email="test_user_2@nowhere.com", password="P@ssw0rd!", tz="UTC")
        self.partner = self.user.partner_id
        self.event = self.env["calendar.event"].create({
            "name": "Doom's day",
            "start": datetime(2019, 10, 25, 8, 0),
            "stop": datetime(2019, 10, 27, 18, 0),
            "partner_ids": [(4, self.partner.id)],
        })

    def test_accept_meeting_unauthenticated(self):
        self.event.write({"partner_ids": [(4, self.other_user.partner_id.id)]})
        attendee = self.event.attendee_ids.filtered(lambda att: att.partner_id.id == self.other_user.partner_id.id)
        token = attendee.access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, self.event.id)
        self.authenticate(None, None)
        res = self.url_open(url, method='POST', data={'csrf_token': self.csrf_token()})

        self.assertEqual(res.status_code, 200, "Response should = OK")
        self.env.invalidate_all()
        self.assertEqual(attendee.state, "accepted", "Attendee should have accepted")

    def test_accept_meeting_authenticated(self):
        self.event.write({"partner_ids": [(4, self.other_user.partner_id.id)]})
        attendee = self.event.attendee_ids.filtered(lambda att: att.partner_id.id == self.other_user.partner_id.id)
        token = attendee.access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, self.event.id)
        self.authenticate("test_user_2", "P@ssw0rd!")
        res = self.url_open(url, method='POST', data={'csrf_token': self.csrf_token()})

        self.assertEqual(res.status_code, 200, "Response should = OK")
        self.env.invalidate_all()
        self.assertEqual(attendee.state, "accepted", "Attendee should have accepted")

    def test_join_videocall_unauthenticated(self):
        self.event.user_id = self.other_user
        self.event._set_discuss_videocall_location()
        self.authenticate(None, None)
        res = self.url_open(f"/calendar/join_videocall/{self.event.access_token}")
        self.assertEqual(res.status_code, 200, "Response should = OK")
        self.assertEqual(
            self.event.videocall_channel_id.create_uid,
            self.other_user,
            "The organizer should create the channel, as they are shown as the inviter",
        )
