# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import math

from odoo.http import Controller
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import HttpCase
from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.mail.tools.discuss import Store, mail_route


class TestStoreVersioning(HttpCase, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, "admin_user", groups="base.group_erp_manager")

        class StoreVersionController(Controller):
            @mail_route("/store/version/write_fields", type="jsonrpc")
            def write_fields(self, fields_to_write_by_id):
                store = Store()
                for key, values in fields_to_write_by_id.items():
                    model_name, record_id = key.split(":")
                    record = self.env[model_name].browse(int(record_id))
                    record.write(values)
                    store.add(record, list(values.keys()))
                return store

            @mail_route("/store/version/read_fields", type="jsonrpc")
            def read_fields(self, fields_to_read_by_id):
                store = Store()
                for key, fnames in fields_to_read_by_id.items():
                    model_name, record_id = key.split(":")
                    store.add(self.env[model_name].browse(int(record_id)), fnames)
                return store

            @mail_route("/store/version/send_bus_notifications", type="jsonrpc")
            def send_bus_notifications(self, fields_by_channel):
                for channel, fields in fields_by_channel.items():
                    model_name, record_id = channel.split(":")
                    record = self.env[model_name].browse(int(record_id))
                    Store(bus_channel=record).add(record, fields)

        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def test_store_versioning_tracks_updated_fields(self):
        self.authenticate("admin_user", "admin_user")
        bob = self.env["res.partner"].create({"name": "bob"})
        alice = self.env["res.partner"].create({"name": "alice"})
        general = self.env["discuss.channel"].create({"name": "general"})
        result = self.make_jsonrpc_request(
            "/store/version/write_fields",
            {
                "fields_to_write_by_id": {
                    f"res.partner:{bob.id}": {"name": "BobNewName", "email": "bob@test.com"},
                    f"res.partner:{alice.id}": {"name": "AliceNewName"},
                    f"discuss.channel:{general.id}": {"description": "General description"},
                },
            },
        )
        written_fields_by_record = result["__store_version__"]["written_fields_by_record"]
        self.assertTrue(
            {
                "complete_name",
                "email",
                "email_normalized",
                "name",
                "write_date",
                "write_uid",
            }.issubset(written_fields_by_record["res.partner"][str(bob.id)]),
        )
        self.assertTrue(
            {"complete_name", "name", "write_date", "write_uid"}.issubset(
                written_fields_by_record["res.partner"][str(alice.id)],
            ),
        )
        self.assertTrue(
            {"description", "write_date", "write_uid"}.issubset(
                written_fields_by_record["discuss.channel"][str(general.id)]
            ),
        )
        result = self.make_jsonrpc_request(
            "/store/version/read_fields",
            {"fields_to_read_by_id": {f"res.partner:{bob.id}": ["name", "email"]}},
        )
        self.assertFalse(result["__store_version__"]["written_fields_by_record"])

    def test_store_versioning_sends_snapshot_data(self):
        self.authenticate("admin_user", "admin_user")
        bob = self.env["res.partner"].create({"name": "bob"})
        result = self.make_jsonrpc_request(
            "/store/version/write_fields",
            {
                "fields_to_write_by_id": {
                    f"res.partner:{bob.id}": {"name": "BobNewName", "email": "bob@test.com"},
                },
            },
        )
        snapshot = result.pop("__store_version__")["snapshot"]
        self.assertIn("xmin", snapshot)
        self.assertIn("xmax", snapshot)
        self.assertIn("xip_bitmap", snapshot)
        self.assertIn("current_xact_id", snapshot)
        result = self.make_jsonrpc_request(
            "/store/version/read_fields",
            {
                "fields_to_read_by_id": {
                    f"res.partner:{bob.id}": ["name", "email"],
                },
            },
        )
        snapshot = result["__store_version__"]["snapshot"]
        self.assertIn("xmin", snapshot)
        self.assertIn("xmax", snapshot)
        self.assertIn("xip_bitmap", snapshot)

    def test_store_version_sent_alongside_bus_notifications(self):
        self.authenticate("admin_user", "admin_user")
        bob = new_test_user(self.env, login="bob", groups="base.group_user")
        general = self.env["discuss.channel"].create({"name": "general"})
        self._reset_bus()
        self.env.cr.execute("""
            SELECT pg_current_snapshot(), pg_current_xact_id_if_assigned()
        """)
        snapshot, current_xact_id = self.env.cr.fetchone()
        snapshot_parts = snapshot.split(":")
        xmin = int(snapshot_parts[0])
        xmax = int(snapshot_parts[1])
        xip = {int(xid) for xid in snapshot_parts[2].split(",") if xid}
        bitmap = bytearray(math.ceil((xmax - xmin) / 8))
        for x in xip:
            offset = x - xmin
            byte_idx = offset // 8
            bit_idx = offset % 8
            bitmap[byte_idx] |= 1 << bit_idx
        expected_snapshot = {
            "xmin": str(xmin),
            "xmax": str(xmax),
            "xip_bitmap": base64.b64encode(bitmap),
            "current_xact_id": current_xact_id,
        }
        with self.assertBus(
            [
                BusResult(
                    bob,
                    "mail.record/insert",
                    {
                        "res.users": [{"id": bob.id, "name": "bob (base.group_user)"}],
                        "__store_version__": {
                            "snapshot": expected_snapshot,
                            "written_fields_by_record": {},
                        },
                    },
                ),
                BusResult(
                    general,
                    "mail.record/insert",
                    {
                        "discuss.channel": [{"id": general.id, "name": "general"}],
                        "__store_version__": {
                            "snapshot": expected_snapshot,
                            "written_fields_by_record": {},
                        },
                    },
                ),
            ],
            show_store_versioning=True,
        ):
            self.make_jsonrpc_request(
                "/store/version/send_bus_notifications",
                {
                    "fields_by_channel": {
                        f"res.users:{bob.id}": ["name"],
                        f"discuss.channel:{general.id}": ["name"],
                    },
                },
            )
