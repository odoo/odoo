# Part of Odoo. See LICENSE file for full copyright and licensing details.
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

    def test_store_versioning_sends_write_date(self):
        self.authenticate("admin_user", "admin_user")
        bob = self.env["res.partner"].create({"name": "bob"})
        result = self.make_jsonrpc_request(
            "/store/version/write_fields",
            {
                "fields_to_write_by_id": {
                    f"res.partner:{bob.id}": {"name": "BobNewName"},
                },
            },
        )
        self.assertEqual(
            result["res.partner"][0]["__version__"],
            bob.write_date.isoformat(timespec="microseconds"),
        )
        result = self.make_jsonrpc_request(
            "/store/version/read_fields",
            {
                "fields_to_read_by_id": {
                    f"res.partner:{bob.id}": ["name"],
                },
            },
        )
        self.assertEqual(
            result["res.partner"][0]["__version__"],
            bob.write_date.isoformat(timespec="microseconds"),
        )

    def test_store_version_sent_alongside_bus_notifications(self):
        self.authenticate("admin_user", "admin_user")
        bob = new_test_user(self.env, login="bob", groups="base.group_user")
        self._reset_bus()
        with self.assertBus(
            [
                BusResult(
                    bob,
                    "mail.record/insert",
                    {
                        "res.users": [
                            {
                                "id": bob.id,
                                "name": "bob (base.group_user)",
                                "__version__": bob.write_date.isoformat(timespec="microseconds"),
                            }
                        ],
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
                    },
                },
            )
