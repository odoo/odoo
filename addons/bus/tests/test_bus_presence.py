# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests import HttpCase, tagged, new_test_user
from ..models.bus_presence import PRESENCE_OUTDATED_TIMER
from odoo.addons.bus.models.bus import channel_with_db, json_dump


@tagged("-at_install", "post_install")
class TestBusPresence(HttpCase):
    def test_bus_presence_auto_vacuum(self):
        user = new_test_user(self.env, login="bob_user")
        # presence is outdated
        more_than_away_timer_ago = datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER + 1)
        more_than_away_timer_ago = more_than_away_timer_ago.replace(microsecond=0)
        with freeze_time(more_than_away_timer_ago):
            self.env["bus.presence"]._update_presence(
                inactivity_period=0, identity_field="user_id", identity_value=user.id
            )
        presence = self.env["bus.presence"].search([("user_id", "=", user.id)])
        self.assertEqual(presence.last_poll, more_than_away_timer_ago)
        self.env["bus.presence"]._gc_bus_presence()
        presence = self.env["bus.presence"].search([("user_id", "=", user.id)])
        self.assertFalse(presence)

    def test_im_status_invalidation(self):
        bob_user = new_test_user(self.env, login="bob_user")
        self.assertEqual(bob_user.im_status, "offline")
        self.env["bus.presence"]._update_presence(
            inactivity_period=0, identity_field="user_id", identity_value=bob_user.id
        )
        self.assertEqual(bob_user.im_status, "online")

    def test_unlinking_sends_correct_im_status(self):
        bob = new_test_user(self.env, login="bob_userg", groups="base.group_user")
        self.env["bus.presence"]._update_presence(
            inactivity_period=0, identity_field="user_id", identity_value=bob.id
        )
        self.env["bus.presence"].search([("user_id", "=", bob.id)]).unlink()
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        channel = json_dump(channel_with_db(self.env.cr.dbname, (bob.partner_id, "presence")))
        bus_notif = self.env["bus.bus"].sudo().search(
            [("channel", "=", channel)], order="id desc", limit=1,
        )
        self.assertEqual(json.loads(bus_notif.message)["payload"]["presence_status"], "offline")
        self.assertEqual(json.loads(bus_notif.message)["payload"]["im_status"], "offline")
