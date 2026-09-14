import importlib.util
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

_MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
_MIGRATION = next(
    (
        candidate
        for name in ("1.6.0", "19.0.1.6.0")
        if (candidate := _MIGRATIONS / name / "pre-migrate.py").is_file()
    ),
    _MIGRATIONS / "1.6.0" / "pre-migrate.py",
)

_LIVE_EXPIRY_CRON = "credential.ir_cron_check_expiring_credentials"


def _load_migration():
    spec = importlib.util.spec_from_file_location("integration_dissolution", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install", "integration")
class TestOrphanCronMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.migration = _load_migration()
        self._seed_gateway_module()

    def _seed_gateway_module(self):
        self.env.cr.execute(
            "SELECT id FROM ir_module_module WHERE name = 'api_gateway'",
        )
        if self.env.cr.fetchone():
            return
        self.env.cr.execute(
            """
            INSERT INTO ir_module_module (name, state, auto_install, application)
            VALUES ('api_gateway', 'installed', false, false)
            """,
        )

    def _seed_gateway_cron(self, name):
        cron = (
            self.env["ir.cron"]
            .sudo()
            .create(
                {
                    "name": f"Stale {name}",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "state": "code",
                    "code": "model.browse()",
                    "repeat_interval": 1,
                    "repeat_unit": "day",
                }
            )
        )
        self.env["ir.model.data"].sudo().create(
            {
                "module": "api_gateway",
                "name": name,
                "model": "ir.cron",
                "res_id": cron.id,
            }
        )
        return cron

    def _run(self):
        self.env.flush_all()
        self.migration.migrate(self.env.cr, "19.0.1.5.0")
        self.env.invalidate_all()

    def test_the_duplicate_expiry_cron_is_deleted_not_adopted(self):
        cron = self._seed_gateway_cron("cron_check_expiring_credentials")
        self._run()
        self.assertFalse(cron.exists(), "the duplicate expiry cron was adopted")
        self.assertFalse(
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("module", "=", "integration"),
                    ("name", "=", "cron_check_expiring_credentials"),
                ]
            ),
            "its xmlid was re-homed instead of dropped",
        )

    def test_the_orphaned_crons_are_deleted(self):
        crons = [
            self._seed_gateway_cron(name)
            for name in ("cron_health_check_services", "cron_reset_cache_errors")
        ]
        self._run()
        for cron in crons:
            self.assertFalse(cron.exists())

    def test_the_live_expiry_cron_survives(self):
        mine = self.env.ref(_LIVE_EXPIRY_CRON)
        self._seed_gateway_cron("cron_check_expiring_credentials")
        self._run()
        self.assertTrue(mine.exists(), "the surviving expiry cron was removed")

    def test_idempotent_when_nothing_is_stale(self):
        self._run()
        self._run()
        self.assertTrue(self.env.ref(_LIVE_EXPIRY_CRON).exists())
