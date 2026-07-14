import gc
import time
import weakref
from types import SimpleNamespace
from unittest.mock import patch

import odoo.orm.registry
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install')
class TestRegistry(TransactionCase):
    def test_setup_models_field_leak(self, model_names=None):
        registry = self.registry
        # start with an empty cache
        for cache_name in self.env.transaction.ormcaches__:
            if '.' not in cache_name:
                self.env.transaction.invalidate_ormcache(cache_name)
        registry._setup_models__(self.cr)  # clean start

        # Take the snapshot of instantiated fields
        pre_fields = weakref.WeakSet()
        for model_class in registry.values():
            pre_fields.update(model_class._fields.values())
        pre_count = len(pre_fields)

        # make sure we have cached properties filled
        with self.muted_registry_logger:
            for name in dir(registry):
                getattr(registry, name)  # fill cached properties
            for field in pre_fields:
                registry.is_modifying_relations(field)
                registry.get_field_trigger_tree(field)
            del field
            registry.check_null_constraints(self.cr)
            self.env.user.read()  # run some code

        # Re-setup models
        if model_names is None:
            registry._setup_models__(self.cr)
        else:
            registry._setup_models__(self.cr, model_names)
            registry.field_setup_dependents.clear()  # filled during incremental setup

        # stuff may remain in the cache, clear it
        for cache_name in self.env.transaction.ormcaches__:
            if '.' not in cache_name:
                self.env.transaction.invalidate_ormcache(cache_name)
        self.env.cr.transaction._recent_envs.clear()

        # Now collect objects
        # This test may fail if your debugger stores references to previous fields.
        gc.collect(2)  # full GC
        pre_fields = set(pre_fields)

        # Current fields
        post_fields = set()
        for model_class in registry.values():
            post_fields.update(model_class._fields.values())
        self.assertEqual(len(post_fields), pre_count, "Same number of fields")

        # Show detailed leaks
        remaining_fields = pre_fields - post_fields
        if remaining_fields:
            show = 10
            info = [f"Unused fields should be deallocated: {len(remaining_fields)} left of {len(post_fields)}"]

            def exclude(v):
                return v is pre_fields or v is remaining_fields or 'pydev' in type(v).__module__

            for field in remaining_fields:
                referrers = gc.get_referrers(field)
                show_referrers = {
                    repr(r)[:100]: [
                        repr(r2)[:100]
                        for r2 in gc.get_referrers(r)
                        if not exclude(r2)
                    ]
                    for r in referrers
                    if not exclude(r)
                }
                info.append(f"- left field {field}, referenced by:\n{show_referrers}")
                show -= 1
                if not show:
                    info.append('...')
                    break
            self.fail('\n'.join(info))

    def test_setup_models_field_leak_partial(self):
        self.test_setup_models_field_leak(('res.users', 'res.company'))


@tagged('post_install')
class TestRegistryGC(TransactionCase):
    def _add_fake_registry(self, name, *, ready, last_used):
        """ Register a lightweight stand-in registry and ensure it is removed
        after the test, whatever the outcome. ``_gc_registries`` only reads
        ``ready`` and ``_last_used``, so a namespace is enough.
        """
        Registry.registries[name] = SimpleNamespace(ready=ready, _last_used=last_used)
        self.addCleanup(Registry.registries.pop, name, None)

    def test_gc_collects_only_idle_ready_registries(self):
        now = time.monotonic()
        self._add_fake_registry("__gc_idle__", ready=True, last_used=now - 10_000)
        self._add_fake_registry("__gc_fresh__", ready=True, last_used=now)
        self._add_fake_registry("__gc_loading__", ready=False, last_used=now - 10_000)

        with patch.object(odoo.orm.registry, '_REGISTRY_GC_TIMEOUT', 60):
            Registry._gc_registries()

        self.assertNotIn("__gc_idle__", Registry.registries, "an idle registry should be collected")
        self.assertIn("__gc_fresh__", Registry.registries, "a recently used registry should be kept")
        self.assertIn("__gc_loading__", Registry.registries, "a registry still loading should never be collected")

    def test_gc_disabled_when_timeout_not_positive(self):
        self._add_fake_registry("__gc_idle__", ready=True, last_used=time.monotonic() - 10_000)

        with patch.object(odoo.orm.registry, '_REGISTRY_GC_TIMEOUT', 0):
            Registry._gc_registries()

        self.assertIn("__gc_idle__", Registry.registries,"GC must be a no-op when the timeout is not positive")

    def test_access_refreshes_last_used(self):
        registry = self.registry
        registry._last_used = 0.0
        # fetching the registry again must stamp it as freshly used
        self.assertIs(Registry(registry.db_name), registry)
        self.assertGreater(registry._last_used, 0.0)
