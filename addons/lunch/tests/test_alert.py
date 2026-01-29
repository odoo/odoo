# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from odoo import fields
from odoo.tests import common
from odoo.addons.lunch.tests.common import TestsCommon


class TestAlarm(TestsCommon):
    @common.users('cle-lunch-manager')
    def test_cron_sync_create(self):
        cron_ny = self.alert_ny.cron_id
        self.assertTrue(cron_ny.active)
        self.assertEqual(cron_ny.name, "Lunch: alert chat notification (New York UTC-5)")
        self.assertEqual(
            [line for line in cron_ny.code.splitlines() if not line.lstrip().startswith("#")],
            ["env['lunch.alert'].browse([%i])._notify_chat()" % self.alert_ny.id])
        self.assertEqual(cron_ny.nextcall, datetime(2021, 1, 29, 15, 0))  # New-york is UTC-5

        tokyo_cron = self.alert_tokyo.cron_id
        self.assertEqual(tokyo_cron.nextcall, datetime(2021, 1, 29, 23, 0))  # Tokyo is UTC+9 but the cron is posponed

    @common.users('cle-lunch-manager')
    def test_cron_sync_active(self):
        cron_ny = self.alert_ny.cron_id

        self.alert_ny.active = False
        self.assertFalse(cron_ny.active)
        self.alert_ny.active = True
        self.assertTrue(cron_ny.active)

        self.alert_ny.mode = 'alert'
        self.assertFalse(cron_ny.active)
        self.alert_ny.mode = 'chat'
        self.assertTrue(cron_ny.active)

        ctx_today = fields.Date.context_today(self.alert_ny, self.fakenow)
        self.alert_ny.until = ctx_today - timedelta(days=1)
        self.assertFalse(cron_ny.active)
        self.alert_ny.until = ctx_today + timedelta(days=2)
        self.assertTrue(cron_ny.active)
        self.alert_ny.until = False
        self.assertTrue(cron_ny.active)

    @common.users('cle-lunch-manager')
    def test_cron_sync_nextcall(self):
        cron_ny = self.alert_ny.cron_id
        old_nextcall = cron_ny.nextcall

        self.alert_ny.notification_time -= 5
        self.assertEqual(cron_ny.nextcall, old_nextcall - timedelta(hours=5) + timedelta(days=1))

        # Simulate cron execution
        cron_ny.sudo().lastcall = old_nextcall - timedelta(hours=5)
        cron_ny.sudo().nextcall += timedelta(days=1)

        self.alert_ny.notification_time += 7
        self.assertEqual(cron_ny.nextcall, old_nextcall + timedelta(days=1, hours=2))

        self.alert_ny.notification_time -= 1
        self.assertEqual(cron_ny.nextcall, old_nextcall + timedelta(days=1, hours=1))
