from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import SQL

GATE_LOGGER = "odoo.addons.approval.models.approval_gate"


@tagged("post_install", "-at_install")
class TestGateSync(TransactionCase):
    """A registry that does not declare a gate archives it only when the code
    that declared it is gone, and the gate keeps its enforcement either way."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Gate = cls.env["approval.gate"].with_context(active_test=False)
        cls.ship = cls.Gate.search(
            [
                ("model_name", "=", "approval.test.gated"),
                ("operation", "=", "action_ship"),
            ]
        )
        cls.ship.enforced = True
        cls.declared = cls.env["approval.gate"]._get_declared_operations()

    def _gate(self, model_name):
        return self.Gate.create(
            {"model_name": model_name, "operation": "action_ship", "enforced": True}
        )

    def _model_owned_by(self, model_name, module):
        self.env.cr.execute(
            SQL(
                """
                WITH model AS (
                    INSERT INTO ir_model (model, name, "order", state, transient)
                    VALUES (%s, jsonb_build_object('en_US', %s::text), 'id', 'base', false)
                    RETURNING id
                )
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                SELECT %s::varchar, %s::varchar, 'ir.model', model.id, false FROM model
                """,
                model_name,
                model_name,
                module,
                "model_" + model_name.replace(".", "_"),
            )
        )

    def _sync(self, declared=None):
        Gate = self.env["approval.gate"]
        declared = self.declared if declared is None else declared
        with patch.object(
            type(Gate), "_get_declared_operations", lambda self: declared
        ):
            Gate._sync_declared_gates()

    def _without_ship(self):
        return self.declared - {("approval.test.gated", "action_ship")}

    def test_a_gate_whose_model_this_registry_did_not_load_keeps_enforcing(self):
        gate = self._gate("approval.test.unloaded")
        self._model_owned_by("approval.test.unloaded", "test_approval")

        self._sync()

        self.assertTrue(gate.exists(), "an installed module's gate is not deleted")
        self.assertRecordValues(gate, [{"active": True, "enforced": True}])

    def test_a_module_installed_but_not_loaded_leaves_every_gate_alone(self):
        registry = self.env.registry
        with (
            patch.object(
                registry, "loaded_modules", registry.loaded_modules - {"test_approval"}
            ),
            self.assertLogs(GATE_LOGGER, "WARNING") as logs,
        ):
            self._sync(self._without_ship())

        self.assertTrue(self.ship.exists())
        self.assertRecordValues(self.ship, [{"active": True, "enforced": True}])
        self.assertIn("test_approval", logs.output[0])
        self.assertIn("approval.test.gated.action_ship", logs.output[0])

    def test_a_gate_whose_module_is_not_installed_is_archived_with_its_decision(self):
        gone = self._gate("approval.test.gone")
        uninstalled = self.env["ir.module.module"].search(
            [("state", "=", "uninstalled")], limit=1
        )
        self.assertTrue(uninstalled, "some module of the tree is not installed")
        orphan = self._gate("approval.test.orphan")
        self._model_owned_by("approval.test.orphan", uninstalled.name)
        watching = self._gate("approval.test.watching")
        watching.enforced = False

        with self.assertLogs(GATE_LOGGER, "WARNING") as logs:
            self._sync()

        self.assertRecordValues(
            gone | orphan | watching,
            [
                {"active": False, "enforced": True},
                {"active": False, "enforced": True},
                {"active": False, "enforced": False},
            ],
        )
        self.assertEqual(len(logs.output), 2, "only an enforcing gate is warned of")
        self.assertIn("approval.test.gone.action_ship", logs.output[0])
        self.assertIn("not installed", logs.output[0])

    def test_an_operation_the_loaded_model_no_longer_declares_is_archived(self):
        with self.assertLogs(GATE_LOGGER, "WARNING") as logs:
            self._sync(self._without_ship())

        self.assertRecordValues(self.ship, [{"active": False, "enforced": True}])
        self.assertIn("no longer declares it", logs.output[0])
        self.assertNotIn(
            ("approval.test.gated", "action_ship"),
            self.env["approval.gate"]._get_enforced_operations(),
        )

    def test_an_operation_declared_again_resumes_enforcing(self):
        with self.assertLogs(GATE_LOGGER, "WARNING"):
            self._sync(self._without_ship())

        self._sync()

        self.assertRecordValues(self.ship, [{"active": True, "enforced": True}])
        self.assertEqual(
            self.Gate.search_count([("model_name", "=", "approval.test.gated")]),
            1,
            "the same row comes back, not a watching twin",
        )
        document = self.env["approval.test.gated"].create({"name": "Declared again"})
        self.assertTrue(document._is_approval_gate_enforced("action_ship"))
