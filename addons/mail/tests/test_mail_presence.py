# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests import HttpCase, tagged, new_test_user
from ..models.mail_presence import PRESENCE_OUTDATED_TIMER


@tagged("-at_install", "post_install")
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
