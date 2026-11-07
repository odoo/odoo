# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests import HttpCase, new_test_user
from ..models.mail_presence import PRESENCE_OUTDATED_TIMER
from odoo.addons.bus.tests.common import BusCase, BusResult


class TestMailPresence(BusCase, HttpCase):
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
        with self.assertBus(
            [
                BusResult(
                    (bob, "presence"),
                    "mail.record/insert",
                    {"res.users": [{"id": bob.id, "im_status": "offline"}]},
                ),
                BusResult(
                    bob,
                    "mail.record/insert",
                    {"res.users": [{"id": bob.id, "presence_status": "offline"}]},
                ),
            ],
        ):
            self.env["mail.presence"].search([("user_id", "=", bob.id)]).unlink()
