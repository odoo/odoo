import gc
import time
import weakref
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields, models
from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, TransactionCase, tagged


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

    def test_init_descendants_false(self):
        """Adding a method to base must make it available on res.partner without
        initializing res.partner's database structures. Initializing base itself
        must still create the module's model XML ID on install and keep it on upgrade.
        """
        registry = self.registry
        base_model = registry['base']
        partner_model = registry['res.partner']
        module = SimpleNamespace(name='test_base')
        self.env.transaction.will_change_registry()
        # SQL rollback does not restore model definitions; restore their bases too.
        with (
            patch.dict(models.MetaModel._module_to_models__, {module.name: []}),
            patch.object(base_model, '_base_classes__', base_model._base_classes__),
        ):
            class BaseExtension(models.AbstractModel):
                _inherit = 'base'
                _init_descendants = False

                def _test_inherited_method(self):
                    return 'Method inherited from base'

            # Load the extension as the module loader would, before the registry is ready.
            with patch.object(registry, 'ready', False):
                loaded_model_names = registry.load(module)
            self.assertFalse(partner_model._setup_done__)

            # Python setup must still give res.partner the method added to base.
            registry._setup_models__(self.cr, [])
            self.assertEqual(
                self.env['res.partner']._test_inherited_method(),
                'Method inherited from base',
            )

            # Only base needs database initialization, not its descendant res.partner.
            models_to_init = registry._get_models_to_init(module, loaded_model_names)
            self.assertEqual(list(models_to_init), ['base'])
            with (
                patch.object(partner_model, '_auto_init') as partner_auto_init,
                patch.object(partner_model, 'init') as partner_init,
            ):
                for operation, install in [('install', True), ('upgrade', False)]:
                    with self.subTest(operation=operation):
                        registry.init_models(self.cr, models_to_init, {'module': module.name}, install=install)
                        partner_auto_init.assert_not_called()
                        partner_init.assert_not_called()

                        # The module must get its own XML ID pointing to the existing base model.
                        self.assertEqual(self.env.ref('test_base.model_base'), self.env.ref('base.model_base'))


class TestInitDescendants(BaseCase):
    """Test which models are selected, without initializing any database tables."""

    def setUp(self):
        super().setUp()
        self.module = SimpleNamespace(name='test_init_descendants')
        # Collect temporary extensions here instead of adding them to a real module.
        self.startPatcher(patch.dict(models.MetaModel._module_to_models__, {self.module.name: []}))

        # base -> parent -> child use Python inheritance (_inherit).
        # child -> delegated uses delegation (_inherits).
        # Extending base therefore affects all four models.
        self.model_hierarchy = {
            'base': SimpleNamespace(_name='base', _inherit_children=['parent'], _inherits_children=[]),
            'parent': SimpleNamespace(_name='parent', _inherit_children=['child'], _inherits_children=[]),
            'child': SimpleNamespace(_name='child', _inherit_children=[], _inherits_children=['delegated']),
            'delegated': SimpleNamespace(_name='delegated', _inherit_children=[], _inherits_children=[]),
        }

    def _add_extension(self, model_name='base', **attributes):
        """Create a model extension; the metaclass registers it in our test module."""
        return type('Extension', (models.AbstractModel,), {
            '_module': self.module.name,
            '_name': model_name,
            '_inherit': model_name,
            **attributes,
        })

    def _select_models_to_initialize(self):
        """Run the real selection and inheritance traversal on our small hierarchy."""
        registry = SimpleNamespace(
            descendants=lambda *args: Registry.descendants(self.model_hierarchy, *args),
        )
        definitions = models.MetaModel._module_to_models__[self.module.name]
        directly_modified_models = [definition._name for definition in definitions]
        return Registry._get_models_to_init(registry, self.module, directly_modified_models)

    def test_descendants_are_initialized_unless_the_extension_opts_out(self):
        """A methods-only extension needs an explicit opt-out, for every _inherit form."""
        for scenario, attributes, expected_models in [
            ('default', {}, ['base', 'parent', 'child', 'delegated']),
            ('opt out', {'_init_descendants': False}, ['base']),
        ]:
            for inheritance in ('base', ['base'], ('base',)):
                with (
                    self.subTest(scenario=scenario, inheritance=inheritance),
                    patch.dict(models.MetaModel._module_to_models__, {self.module.name: []}),
                ):
                    self._add_extension(_inherit=inheritance, _query=lambda self: 'SELECT 1', **attributes)
                    self.assertEqual(list(self._select_models_to_initialize()), expected_models)

    def test_opt_out_cannot_remove_models_required_by_another_extension(self):
        """Keep required descendants across different models, classes, and load orders."""
        for scenario, extensions, expected_models in [
            ('field added to parent', [
                ('base', {'_init_descendants': False}),
                ('parent', {'value': fields.Char()}),
            ], ['base', 'parent', 'child', 'delegated']),
            ('same model, opt-out first', [
                ('base', {'_init_descendants': False}),
                ('base', {'_init_descendants': True}),
            ], ['base', 'parent', 'child', 'delegated']),
            ('same model, opt-out last', [
                ('base', {'_init_descendants': True}),
                ('base', {'_init_descendants': False}),
            ], ['base', 'parent', 'child', 'delegated']),
            ('base requires an opted-out descendant', [
                ('parent', {'_init_descendants': False}),
                ('base', {}),
            ], ['parent', 'base', 'child', 'delegated']),
        ]:
            with (
                self.subTest(scenario=scenario),
                patch.dict(models.MetaModel._module_to_models__, {self.module.name: []}),
            ):
                for model_name, attributes in extensions:
                    self._add_extension(model_name, **attributes)
                self.assertEqual(list(self._select_models_to_initialize()), expected_models)

    def test_new_extension_does_not_inherit_the_opt_out(self):
        """A Python subclass adding a field must default to initializing descendants."""
        class MethodsOnlyExtension(models.AbstractModel):
            _module = self.module.name
            _inherit = 'base'
            _init_descendants = False

        class ExtensionWithField(MethodsOnlyExtension):
            _module = self.module.name
            _inherit = 'base'

            value = fields.Char()

        self.assertCountEqual(self._select_models_to_initialize(), ['base', 'parent', 'child', 'delegated'])

    def test_database_changes_cannot_opt_out(self):
        """Reject opt-outs on extensions with database changes or new model parents."""
        for declaration, attributes in [
            ('field', {'value': fields.Char()}),
            ('index', {'_index': models.Index('(id)')}),
            ('constraint', {'_constraint': models.Constraint('CHECK (id > 0)', 'Positive ID required')}),
            ('init hook', {'init': lambda self: None}),
            ('auto-init hook', {'_auto_init': lambda self: None}),
            ('SQL view query', {'_table_query': 'SELECT 1'}),
            ('default ordering', {'_order': 'name'}),
            ('fold field', {'_fold_name': 'is_folded'}),
            ('delegated parent', {'_inherits': {'parent': 'parent_id'}}),
            ('additional inherited parent', {'_inherit': ['base', 'parent']}),
            ('new model', {'_inherit': [], '_name': 'new.model'}),
        ]:
            with self.subTest(declaration=declaration):
                with self.assertRaisesRegex(TypeError, '_init_descendants=False'):
                    self._add_extension(_init_descendants=False, **attributes)
                # A rejected definition must not be left for the module loader to use.
                self.assertEqual(models.MetaModel._module_to_models__[self.module.name], [])


@tagged('post_install')
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
