# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestGamificationCron(TransactionCase):
    def test_get_cron_update_interval_or_default_interval(self):
        # Check that we get the lower frequency set on the cron.
        self.env.ref("gamification.ir_cron_check_challenge").write({
            "interval_type": "hours",
            "interval_number": 12,
        })
        self.assertEqual(12*60*60, self.env["gamification.challenge"]._get_cron_update_interval_or_default())

    @mute_logger('odoo.models.unlink')
    def test_get_cron_update_interval_or_default_default(self):
        """Test that the method returns 24h if the record isn't found."""
        cron = self.env.ref("gamification.ir_cron_check_challenge")
        cron.unlink()
        self.assertEqual(24*60*60, self.env["gamification.challenge"]._get_cron_update_interval_or_default())
