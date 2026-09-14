import importlib.util
from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


MIGRATION = Path(__file__).resolve().parents[1] / "migrations/1.27.0/post-migrate.py"


def _migrate(env):
    spec = importlib.util.spec_from_file_location("integration_1_27_0", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(env.cr, "1.26.0")


@tagged("post_install", "-at_install", "integration")
class TestCustomApiTemplateRemoval(TransactionCase):
    def _seeded_template(self, **overrides):
        service = self.env["integration.service"].create(
            {
                "name": "Custom API Integration",
                "code": "custom_api",
                "endpoint_url": "https://api.example.com",
                "auth_type": "bearer",
                **overrides,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "integration",
                "name": "service_custom_api",
                "model": "integration.service",
                "res_id": service.id,
                "noupdate": True,
            }
        )
        return service

    def test_an_untouched_template_is_deleted(self):
        service = self._seeded_template()

        _migrate(self.env)

        self.assertFalse(service.exists())

    def test_a_template_someone_pointed_elsewhere_is_kept(self):
        service = self._seeded_template(endpoint_url="https://erp.partner.test")

        _migrate(self.env)

        self.assertTrue(service.exists())

    def test_a_template_holding_a_credential_is_kept(self):
        service = self._seeded_template()
        self.env["credential.credential"].create(
            {
                "name": "Custom API token",
                "category_id": self.env.ref(
                    "credential.credential_category_bearer_token"
                ).id,
                "bearer_token": "token",
                "endpoint_id": service.id,
            }
        )

        _migrate(self.env)

        self.assertTrue(service.exists())
