from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


def just_raise(*args):
    msg = "We should not be here."
    raise Exception(msg)


@tagged("post_install", "-at_install")
class TestResConfigInstall(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.ref("base.user_admin")
        self.company = self.env["res.company"].create({"name": "oobO"})
        self.user.write(
            {
                "company_ids": [(4, self.company.id)],
                "company_id": self.company.id,
            }
        )
        Settings = self.env["res.config.settings"].with_user(self.user.id)
        self.config = Settings.create({})

    def test_no_install(self):
        config_fields = self.config._get_fields_classified()
        for module in config_fields["module"]:
            if self.config[f"module_{module.name}"]:
                self.assertTrue(
                    module.state != "uninstalled",
                    "All set modules should already be installed.",
                )
        with patch(
            "odoo.addons.base.models.ir_module.IrModuleModule.button_immediate_install",
            new=just_raise,
        ):
            self.config.execute()

    def test_install(self):
        config_fields = self.config._get_fields_classified()
        module_to_install = next(
            (m for m in config_fields["module"] if m.state == "uninstalled"),
            None,
        )
        if module_to_install is None:
            self.skipTest("No uninstalled modules available in this database")
        self.config[f"module_{module_to_install.name}"] = True

        with patch(
            "odoo.addons.base.models.ir_module.IrModuleModule.button_immediate_install",
            new=just_raise,
        ):
            with self.assertRaisesRegex(Exception, "We should not be here."):
                self.config.execute()

    def test_install_survives_an_uninstall_in_the_same_save(self):
        config_fields = self.config._get_fields_classified()
        uninstalled = [m for m in config_fields["module"] if m.state == "uninstalled"]
        if len(uninstalled) < 2:
            self.skipTest("Needs two uninstalled settings modules")
        to_install, to_uninstall = uninstalled[:2]
        to_uninstall.sudo().state = "installed"
        self.config[f"module_{to_install.name}"] = True
        self.config[f"module_{to_uninstall.name}"] = False
        installed = []

        def record_install(modules):
            installed.extend(modules.mapped("name"))

        with patch(
            "odoo.addons.base.models.ir_module.IrModuleModule.button_immediate_install",
            new=record_install,
        ):
            action = self.config.execute()

        self.assertEqual(installed, [to_install.name])
        self.assertEqual(action["res_model"], "base.module.uninstall")
        self.assertEqual(action["context"]["default_module_ids"], to_uninstall.ids)
