from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestRegistryHooks(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Rule = self.env["automation.rule"]
        self.model_partner = self.env["ir.model"]._get("res.partner")

    def _rule(self, trigger):
        return self.Rule.create(
            {
                "name": f"Hooks {trigger}",
                "model_id": self.model_partner.id,
                "trigger": trigger,
            }
        )

    @contextmanager
    def _count_registry_updates(self):
        calls = []

        def update_registry(rules):
            calls.append(rules)

        with patch.object(type(self.Rule), "_update_registry", update_registry):
            yield calls

    def test_a_manual_rule_does_not_reload_the_registry(self):
        with self._count_registry_updates() as calls:
            rule = self._rule("on_hand")
            rule.active = False
            rule.active = True
            rule.unlink()

        self.assertEqual(calls, [])

    def test_a_rule_that_patches_models_still_reloads_the_registry(self):
        with self._count_registry_updates() as calls:
            self._rule("on_create")

        self.assertTrue(calls)

    def test_switching_a_rule_away_from_a_patching_trigger_reloads_the_registry(self):
        rule = self._rule("on_create")

        with self._count_registry_updates() as calls:
            rule.trigger = "on_hand"

        self.assertTrue(calls)
