# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import math
from unittest.mock import patch

from odoo.http import Controller
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import HttpCase, TransactionCase
from odoo.addons.mail.models.discuss.discuss_channel import DiscussChannel
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.mail.tools.discuss import Store, mail_route, store_version


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
                return store.get_result()

            @mail_route("/store/version/read_fields", type="jsonrpc")
            def read_fields(self, fields_to_read_by_id):
                store = Store()
                for key, fnames in fields_to_read_by_id.items():
                    model_name, record_id = key.split(":")
                    store.add(self.env[model_name].browse(int(record_id)), fnames)
                return store.get_result()

            @mail_route("/store/version/send_bus_notifications", type="jsonrpc")
            def send_bus_notifications(self, fields_by_channel):
                for channel, fields in fields_by_channel.items():
                    model_name, record_id = channel.split(":")
                    record = self.env[model_name].browse(int(record_id))
                    Store(bus_channel=record).add(record, fields).bus_send()

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
            [bob, general],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "res.users": [{"id": bob.id, "name": "bob (base.group_user)"}],
                        "__store_version__": {
                            "snapshot": expected_snapshot,
                            "written_fields_by_record": {},
                        },
                    },
                },
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "discuss.channel": [{"id": general.id, "name": "general"}],
                        "__store_version__": {
                            "snapshot": expected_snapshot,
                            "written_fields_by_record": {},
                        },
                    },
                },
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


# This test ensures that an "inner" read-only call captures the correct version, and that
# later writes in an "outer" call update the version independently, without affecting the
# previously retrieved inner version.
#
# Using a transaction case as any database modification would assign a TX id right away
# (including `HttpCase.setupClass`).
class TestStoreVersioningTransactionCase(TransactionCase):
    def test_store_version_nested_calls(self):
        @store_version
        def inner(self, fields_to_read):
            store = Store(bus_channel=self).add(self, fields_to_read)
            store.bus_send()
            return store.get_result()

        @store_version
        def outer(self, fields_to_write, fields_to_read):
            inner_store_data = self.inner(fields_to_read)
            self.write(fields_to_write)
            store = Store(bus_channel=self).add(self, [*fields_to_write.keys()])
            store.bus_send()
            return {
                "outer_store_data": store.get_result(),
                "inner_store_data": inner_store_data,
            }

        with (
            patch.object(DiscussChannel, "inner", inner, create=True),
            patch.object(DiscussChannel, "outer", outer, create=True),
        ):
            channel = self.env.ref("mail.channel_all_employees")
            self.env.cr.execute("select pg_current_xact_id_if_assigned()")
            # No TX id at the beginning as the DB wasn't updated.
            self.assertIsNone(self.env.cr.fetchone()[0])
            result = channel.outer(
                fields_to_write={"name": "written"},
                fields_to_read=["description"],
            )
            self.assertEqual(
                result["inner_store_data"]["discuss.channel"],
                [
                    {
                        "id": channel.id,
                        "description": "A place to connect and exchange news with colleagues across the company.",
                    },
                ],
            )
            inner_version = result["inner_store_data"]["__store_version__"]
            # Writes occured after `inner` execution, version should not be impacted by the
            # later writes.
            self.assertFalse(inner_version["snapshot"]["current_xact_id"])
            self.assertFalse(inner_version["written_fields_by_record"])
            self.assertEqual(
                result["outer_store_data"]["discuss.channel"],
                [{"id": channel.id, "name": "written"}],
            )
            outer_version = result["outer_store_data"]["__store_version__"]
            # But `outer` wrote on some fields, version should have been updated.
            self.assertTrue(outer_version["snapshot"]["current_xact_id"])
            self.assertEqual(
                outer_version["written_fields_by_record"],
                {"discuss.channel": {channel.id: ["name", "write_date"]}},
            )
