from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.point_of_sale.models import pos_order as order_module
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestPosDataIntegrity(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self._start_pos_session(self.cash_pm1, 0)

    def test_future_reservations_survive_age_and_session_detachment(self):
        preset = self.env["pos.preset"].create(
            {"name": "Advance reservations", "use_timing": True}
        )
        now = fields.Datetime.now()
        order = self.env["pos.order"].create(
            {
                "session_id": self.pos_session.id,
                "company_id": self.env.company.id,
                "amount_tax": 0,
                "amount_total": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "preset_id": preset.id,
                "preset_time": now + timedelta(days=2, hours=2),
            }
        )
        self.assertTrue(preset._get_slots_usage())
        with freeze_time(now + timedelta(days=2)):
            self.assertTrue(preset._get_slots_usage())
            order.session_id = False
            self.assertTrue(preset._get_slots_usage())
            order.state = "cancel"
            self.assertFalse(preset._get_slots_usage())
            order.write({"state": "draft", "preset_time": now + timedelta(days=30)})
            self.assertFalse(preset._get_slots_usage())
            order.preset_time = now + timedelta(days=2, hours=2)
            for state in ("paid", "done"):
                order.state = state
                self.assertTrue(preset._get_slots_usage())

    def test_timed_presets_require_positive_capacity_and_interval(self):
        for values in (
            {"interval_time": 0},
            {"interval_time": -1},
            {"slots_per_interval": 0},
            {"slots_per_interval": -1},
        ):
            with (
                self.subTest(values=values),
                self.assertRaises(ValidationError),
                self.env.cr.savepoint(),
            ):
                self.env["pos.preset"].create(
                    {"name": "Invalid capacity", "use_timing": True, **values}
                )

    def test_batch_sync_formats_debug_lazily_and_notifies_each_config_once(self):
        values = [
            {
                "uuid": str(uuid4()),
                "session_id": self.pos_session.id,
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "user_id": self.env.uid,
                "state": "draft",
                "amount_total": 0,
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "lines": [],
                "payment_ids": [],
                "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            }
            for _ in range(2)
        ]
        before = len(self.env.cr.precommit.data.get("bus.bus.values", []))
        with (
            patch.object(order_module._logger, "isEnabledFor", return_value=False),
            patch.object(
                order_module, "pformat", wraps=order_module.pformat
            ) as formatted,
        ):
            self.env["pos.order"].sync_from_ui(values)
        messages = self.env.cr.precommit.data.get("bus.bus.values", [])[before:]
        messages = [
            message for message in messages if "SYNCHRONISATION" in message["message"]
        ]
        self.assertEqual(formatted.call_count, 0)
        self.assertEqual(len(messages), 1)
