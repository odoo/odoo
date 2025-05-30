# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests import HttpCase, tagged
from odoo.addons.bus.models.bus import DEFAULT_GC_RETENTION_SECONDS


@tagged("-at_install", "post_install")
class TestBusGC(HttpCase):
    def test_default_gc_retention_window(self):
        self.env["ir.config_parameter"].search([("key", "=", "bus.gc_retention_seconds")]).unlink()
        self.env["bus.bus"].search([]).unlink()
        self.env["bus.bus"].create({"channel": "foo", "message": "bar"})
        self.assertEqual(self.env["bus.bus"].search_count([]), 1)

        with freeze_time(datetime.now() + timedelta(seconds=DEFAULT_GC_RETENTION_SECONDS / 2)):
            self.env["bus.bus"]._gc_messages()
            self.assertEqual(self.env["bus.bus"].search_count([]), 1)
        with freeze_time(datetime.now() + timedelta(seconds=DEFAULT_GC_RETENTION_SECONDS + 1)):
            self.env["bus.bus"]._gc_messages()
            self.assertEqual(self.env["bus.bus"].search_count([]), 0)

    def test_custom_gc_retention_window(self):
        self.env["bus.bus"].search([]).unlink()
        self.env["ir.config_parameter"].set_param("bus.gc_retention_seconds", 25000)
        self.env["bus.bus"].create({"channel": "foo", "message": "bar"})
        self.assertEqual(self.env["bus.bus"].search_count([]), 1)

        with freeze_time(datetime.now() + timedelta(seconds=15000)):
            self.env["bus.bus"]._gc_messages()
            self.assertEqual(self.env["bus.bus"].search_count([]), 1)
        with freeze_time(datetime.now() + timedelta(seconds=30000)):
            self.env["bus.bus"]._gc_messages()
            self.assertEqual(self.env["bus.bus"].search_count([]), 0)
