# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests import HttpCase, new_test_user
from ..models.mail_presence import PRESENCE_OUTDATED_TIMER
from odoo.addons.bus.models.bus import channel_with_db, json_dump


class TestMailPresence(HttpCase):
    def test_bus_presence_auto_vacuum(self):
        user = new_test_user(self.env, login="bob_user")
        more_than_away_timer_ago = datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER + 1)
        more_than_away_timer_ago = more_than_away_timer_ago.replace(microsecond=0)
        with freeze_time(more_than_away_timer_ago):
            self.env["mail.presence"]._update_presence(user)
        self.assertEqual(user.presence_ids.last_poll, more_than_away_timer_ago)
        self.env["mail.presence"]._gc_bus_presence()
        self.assertFalse(user.presence_ids)

    def test_im_status_invalidation(self):
        bob_user = new_test_user(self.env, login="bob_user")
        self.assertEqual(bob_user.im_status, "offline")
        self.env["mail.presence"]._update_presence(bob_user)
        self.assertEqual(bob_user.im_status, "online")

    def test_unlinking_sends_correct_im_status(self):
        bob = new_test_user(self.env, login="bob_userg", groups="base.group_user")
        self.env["mail.presence"]._update_presence(inactivity_period=0, user_or_guest=bob)
        self.env["mail.presence"].search([("user_id", "=", bob.id)]).unlink()
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        presence_channel = json_dump(channel_with_db(self.env.cr.dbname, (bob, "presence")))
        presence_bus_notif = self.env["bus.bus"].sudo().search(
            [("channel", "=", presence_channel)], order="id desc", limit=1,
        )
        user_channel = json_dump(channel_with_db(self.env.cr.dbname, bob))
        user_bus_notif = self.env["bus.bus"].sudo().search(
            [("channel", "=", user_channel)], order="id desc", limit=1,
        )
        self.assertEqual(
            json.loads(presence_bus_notif.message)["payload"]["res.users"][0]["im_status"],
            "offline",
        )
        self.assertEqual(
            json.loads(user_bus_notif.message)["payload"]["res.users"][0]["presence_status"],
            "offline",
        )
