# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from odoo.addons.mail.models.res_config_settings import (
    SFU_CLIENT_SOURCE_URL,
    SFU_CLIENT_TARGET,
)


class TestResConfigSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client_source = "const customSfuClient = true;"
        cls.Attachment = cls.env["ir.attachment"].with_context(website_id=False)
        cls.settings = cls.env["res.config.settings"].create(
            {
                "use_call_server": False,
                "use_sfu_server": False,
                "use_custom_sfu_client": False,
                "sfu_client_source": cls.client_source,
            },
        )

    def _save_client_source(self):
        self.settings.action_save_sfu_client_asset()
        return self.Attachment._get_serve_attachment(SFU_CLIENT_SOURCE_URL)

    def _activate_custom_sfu_client(self):
        self.settings.write(
            {
                "use_call_server": True,
                "use_sfu_server": True,
                "use_custom_sfu_client": True,
            },
        )
        self.settings.execute()
        return self.settings._get_sfu_client_asset()

    def _get_sfu_client_asset_paths(self):
        asset_paths = self.env["ir.asset"]._get_asset_paths("mail.assets_odoo_sfu", {})
        return [path for path, *_ in asset_paths]

    def test_activate_custom_sfu_client_asset(self):
        self._save_client_source()
        client_asset = self._activate_custom_sfu_client()
        self.assertRecordValues(
            client_asset,
            [
                {
                    "name": "Alternative SFU client",
                    "bundle": "mail.assets_odoo_sfu",
                    "directive": "replace",
                    "path": SFU_CLIENT_SOURCE_URL,
                    "target": SFU_CLIENT_TARGET,
                    "active": True,
                },
            ],
        )
        self.assertTrue(self.settings.get_values()["use_custom_sfu_client"])
        self.assertEqual(self._get_sfu_client_asset_paths(), [SFU_CLIENT_SOURCE_URL])

    def test_save_custom_sfu_client_source(self):
        source_attachment = self._save_client_source()
        self.assertEqual(bytes(source_attachment.raw), self.client_source.encode())
        self.assertFalse(self.settings._get_sfu_client_asset())

    def test_update_custom_sfu_client_source(self):
        source_attachment = self._save_client_source()
        client_asset = self._activate_custom_sfu_client()
        updated_source = "const customSfuClient = false;"
        self.settings.sfu_client_source = updated_source
        updated_attachment = self._save_client_source()
        self.assertEqual(updated_attachment, source_attachment)
        self.assertEqual(bytes(source_attachment.raw), updated_source.encode())
        self.assertEqual(self.settings._get_sfu_client_asset(), client_asset)

    def test_disable_custom_sfu_client_asset(self):
        self._save_client_source()
        client_asset = self._activate_custom_sfu_client()
        for disabled_field in (
            "use_call_server",
            "use_sfu_server",
            "use_custom_sfu_client",
        ):
            with self.subTest(disabled_field=disabled_field):
                self.settings.write(
                    {
                        "use_call_server": disabled_field != "use_call_server",
                        "use_sfu_server": disabled_field != "use_sfu_server",
                        "use_custom_sfu_client": disabled_field
                        != "use_custom_sfu_client",
                    },
                )
                self.settings.execute()
                self.assertFalse(client_asset.active)
                self.assertFalse(self.settings.get_values()["use_custom_sfu_client"])
        self.assertEqual(self._get_sfu_client_asset_paths(), [SFU_CLIENT_TARGET])

    def test_reactivate_custom_sfu_client_asset(self):
        source_attachment = self._save_client_source()
        client_asset = self._activate_custom_sfu_client()
        self.settings.use_custom_sfu_client = False
        self.settings.execute()
        self.assertFalse(client_asset.active)
        self._activate_custom_sfu_client()
        self.assertTrue(client_asset.active)
        self.assertEqual(self.settings._get_sfu_client_asset(), client_asset)
        self.assertEqual(
            self.Attachment._get_serve_attachment(SFU_CLIENT_SOURCE_URL),
            source_attachment,
        )

    def test_custom_sfu_client_requires_source(self):
        self.settings.sfu_client_source = " \n\t"
        self._save_client_source()
        with self.assertRaisesRegex(UserError, "Cannot activate custom SFU client"):
            self._activate_custom_sfu_client()
        self.assertFalse(self.settings._get_sfu_client_asset())
