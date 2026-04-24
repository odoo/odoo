import gc
import weakref

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install')
class TestRegistry(TransactionCase):
    def test_setup_models_field_leak(self):
        registry = self.registry
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
        registry._setup_models__(self.cr)
        registry.clear_all_caches()  # stuff may remain in the cache

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
