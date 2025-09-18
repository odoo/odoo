from unittest.mock import patch

from odoo.tests.common import TransactionCase


def just_raise(*args):
    msg = "We should not be here."
    raise Exception(msg)


class TestResConfigInstall(TransactionCase):
    """Tests for res.config.settings module installation logic."""

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
        """When saving settings with no changes, no modules should be installed."""
        config_fields = self.config._get_classified_fields()
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
        """Saving settings with a new module toggled ON should trigger installation."""
        config_fields = self.config._get_classified_fields()
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
