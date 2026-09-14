from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCronOwnership(TransactionCase):
    def _own_crons(self):
        data = self.env["ir.model.data"].search(
            [
                ("module", "=", "integration"),
                ("model", "=", "ir.cron"),
            ]
        )
        return [
            (d.name, self.env["ir.cron"].browse(d.res_id))
            for d in data
            if self.env["ir.cron"].browse(d.res_id).exists()
        ]

    def test_expiring_credentials_cron_is_owned_by_the_vault(self):
        cron = self.env.ref(
            "credential.ir_cron_check_expiring_credentials",
            raise_if_not_found=False,
        )
        self.assertTrue(
            cron,
            "credential.credential.cron_check_expiring_credentials is declared "
            "by credential and must ship with a cron calling it; "
            "without one nothing warns before a credential expires.",
        )
        self.assertEqual(cron.model_id.model, "credential.credential")
        self.assertIn("cron_check_expiring_credentials", cron.code)

    def test_this_module_no_longer_owns_the_expiry_cron(self):
        stale = self.env.ref(
            "integration.ir_cron_check_expiring_credentials",
            raise_if_not_found=False,
        )
        self.assertFalse(
            stale,
            "integration still declares the expiry cron; with the vault's "
            "own record present it would run twice a day instead of once.",
        )

    def test_every_cron_targets_a_method_that_exists(self):
        for name, cron in self._own_crons():
            model = self.env[cron.model_id.model]
            method = cron.code.split("model.", 1)[-1].split("(", 1)[0].strip()
            self.assertTrue(
                hasattr(model, method),
                f"integration.{name} calls {cron.model_id.model}.{method}(), "
                f"which does not exist",
            )

    def test_no_duplicate_cron_for_the_same_method(self):
        seen = {}
        for name, cron in self._own_crons():
            key = (cron.model_id.model, cron.code.strip())
            self.assertNotIn(
                key,
                seen,
                f"integration.{name} duplicates integration.{seen.get(key)}",
            )
            seen[key] = name

    def test_api_gateway_no_longer_owns_the_expiry_cron(self):
        if not self.env["ir.module.module"].search_count(
            [
                ("name", "=", "api_gateway"),
                ("state", "=", "installed"),
            ]
        ):
            self.skipTest("api_gateway is not installed")
        stale = self.env.ref(
            "api_gateway.cron_check_expiring_credentials",
            raise_if_not_found=False,
        )
        self.assertFalse(
            stale,
            "api_gateway still declares the expiry cron; with integration's "
            "own record present it would run twice a day instead of once.",
        )
