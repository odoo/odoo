import time
from types import SimpleNamespace
from unittest.mock import patch

from odoo.modules.registry import Registry
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRegistryGC(TransactionCase):
    def _add_fake_registry(self, name, *, last_used):
        """ Register a lightweight stand-in registry and ensure it is removed
        after the test, whatever the outcome. ``_drop_idle`` only reads
        ``last_used``, so a namespace is enough.
        """
        Registry.registries[name] = SimpleNamespace(last_used=last_used)
        self.addCleanup(Registry.registries.pop, name, None)

    def test_gc_collects_only_idle_registries(self):
        now = time.monotonic()
        self._add_fake_registry("__gc_idle__", last_used=now - 10_000)
        self._add_fake_registry("__gc_fresh__", last_used=now)

        with patch.object(Registry, 'idle_timeout', 60):
            Registry._drop_idle()

        self.assertNotIn("__gc_idle__", Registry.registries, "an idle registry should be collected")
        self.assertIn("__gc_fresh__", Registry.registries, "a recently used registry should be kept")

    def test_gc_disabled_when_timeout_not_positive(self):
        self._add_fake_registry("__gc_idle__", last_used=time.monotonic() - 10_000)

        with patch.object(Registry, 'idle_timeout', 0):
            Registry._drop_idle()

        self.assertIn("__gc_idle__", Registry.registries, "GC must be a no-op when the timeout is not positive")

    def test_access_refreshes_last_used(self):
        registry = self.registry
        last_used = registry.last_used
        # fetching the registry again must stamp it as freshly used
        self.assertIs(Registry(registry.db_name), registry)
        self.assertGreater(registry.last_used, last_used, "accessing a registry should refresh its last_used timestamp")
