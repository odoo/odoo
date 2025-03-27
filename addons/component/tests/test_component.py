# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from contextlib import contextmanager

from odoo.addons.component.core import Component
from odoo.addons.component.exception import NoComponentError, SeveralComponentError

from .common import TransactionComponentRegistryCase


class TestComponent(TransactionComponentRegistryCase):
    """Test usage of components

    These tests are a bit more broad that mere unit tests.
    We test the chain odoo Model -> generate a WorkContext instance -> Work
    with Component.

    Tests are inside Odoo transactions, so we can work
    with Odoo's env / models.
    """

    def setUp(self):
        super().setUp()
        self._setup_registry(self)
        self._setUpComponents()

    def tearDown(self):
        self._teardown_registry(self)
        super().tearDown()

    def _setUpComponents(self):
        # create some Component to play with
        class Component1(Component):
            _name = "component1"
            _collection = "collection.base"
            _usage = "for.test"
            _apply_on = ["res.partner"]

        class Component2(Component):
            _name = "component2"
            _collection = "collection.base"
            _usage = "for.test"
            _apply_on = ["res.users"]

        # build the components and register them in our
        # test component registry
        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)

        # our collection, in a less abstract use case, it
        # could be a record of 'magento.backend' for instance
        self.collection_record = self.collection.new()

        @contextmanager
        def get_base():
            # Our WorkContext, it will be passed along in every
            # components so we can share data transversally.
            # We are working with res.partner in the following tests,
            # unless we change it in the test.
            with self.collection_record.work_on(
                "res.partner",
                # we use a custom registry only
                # for the sake of the tests
                components_registry=self.comp_registry,
            ) as work:
                # We get the 'base' component, handy to test the base
                # methods component, many_components, ...
                yield work.component_by_name("base")

        self.get_base = get_base

    def test_component_attrs(self):
        """Basic access to a Component's attribute"""
        with self.get_base() as base:
            # as we are working on res.partner, we should get 'component1'
            comp = base.work.component(usage="for.test")
            # but this is not what we test here, we test the attributes:
            self.assertEqual(self.collection_record, comp.collection)
            self.assertEqual(base.work, comp.work)
            self.assertEqual(self.env, comp.env)
            self.assertEqual(self.env["res.partner"], comp.model)

    def test_component_get_by_name_same_model(self):
        """Use component_by_name with current working model"""
        with self.get_base() as base:
            # we ask a component directly by it's name, considering
            # we work with res.partner, we should get 'component1'
            # this is ok because it's _apply_on contains res.partner
            comp = base.component_by_name("component1")
            self.assertEqual("component1", comp._name)
            self.assertEqual(self.env["res.partner"], comp.model)

    def test_component_get_by_name_other_model(self):
        """Use component_by_name with another model"""
        with self.get_base() as base:
            # we ask a component directly by it's name, but we
            # want to work with 'res.users', this is ok since
            # component2's _apply_on contains res.users
            comp = base.component_by_name("component2", model_name="res.users")
            self.assertEqual("component2", comp._name)
            self.assertEqual(self.env["res.users"], comp.model)
            # what happens under the hood, is that a new WorkContext
            # has been created for this model, with all the other values
            # identical to the previous WorkContext (the one for res.partner)
            # We can check that with:
            self.assertNotEqual(base.work, comp.work)
            self.assertEqual("res.partner", base.work.model_name)
            self.assertEqual("res.users", comp.work.model_name)

    def test_component_get_by_name_wrong_model(self):
        """Use component_by_name with a model not in _apply_on"""
        msg = (
            "Component with name 'component2' can't be used "
            "for model 'res.partner'.*"
        )
        with self.get_base() as base:
            with self.assertRaisesRegex(NoComponentError, msg):
                # we ask for the model 'component2' but we are working
                # with res.partner, and it only accepts res.users
                base.component_by_name("component2")

    def test_component_get_by_name_not_exist(self):
        """Use component_by_name on a component that do not exist"""
        msg = "No component with name 'foo' found."
        with self.get_base() as base:
            with self.assertRaisesRegex(NoComponentError, msg):
                base.component_by_name("foo")

    def test_component_by_usage_same_model(self):
        """Use component(usage=...) on the same model"""
        # we ask for a component having _usage == 'for.test', and
        # model being res.partner (the model in the current WorkContext)
        with self.get_base() as base:
            comp = base.component(usage="for.test")
            self.assertEqual("component1", comp._name)
            self.assertEqual(self.env["res.partner"], comp.model)

    def test_component_by_usage_other_model(self):
        """Use component(usage=...) on a different model (name)"""
        # we ask for a component having _usage == 'for.test', and
        # a different model (res.users)
        with self.get_base() as base:
            comp = base.component(usage="for.test", model_name="res.users")
            self.assertEqual("component2", comp._name)
            self.assertEqual(self.env["res.users"], comp.model)
            # what happens under the hood, is that a new WorkContext
            # has been created for this model, with all the other values
            # identical to the previous WorkContext (the one for res.partner)
            # We can check that with:
            self.assertNotEqual(base.work, comp.work)
            self.assertEqual("res.partner", base.work.model_name)
            self.assertEqual("res.users", comp.work.model_name)

    def test_component_by_usage_other_model_env(self):
        """Use component(usage=...) on a different model (instance)"""
        with self.get_base() as base:
            comp = base.component(usage="for.test", model_name=self.env["res.users"])
            self.assertEqual("component2", comp._name)
            self.assertEqual(self.env["res.users"], comp.model)

    def test_component_error_several(self):
        """Use component(usage=...) when more than one generic component match"""
        # we create 1 new Component with _usage 'for.test', in the same
        # collection and no _apply_on, and we remove the _apply_on of component
        # 1 so they are generic components for a collection
        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _usage = "for.test"

        class Component1(Component):
            _inherit = "component1"
            _collection = "collection.base"
            _usage = "for.test"
            _apply_on = None

        Component3._build_component(self.comp_registry)
        Component1._build_component(self.comp_registry)

        with self.get_base() as base:
            with self.assertRaises(SeveralComponentError):
                # When a component has no _apply_on, it means it can be applied
                # on *any* model. Here, the candidates components would be:
                # component3 (because it has no _apply_on so apply in any case)
                # component4 (for the same reason)
                base.component(usage="for.test")

    def test_component_error_several_same_model(self):
        """Use component(usage=...) when more than one component match a model"""
        # we create a new Component with _usage 'for.test', in the same
        # collection and no _apply_on
        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _usage = "for.test"
            _apply_on = ["res.partner"]

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            with self.assertRaises(SeveralComponentError):
                # Here, the candidates components would be:
                # component1 (because we are working with res.partner),
                # component3 (for the same reason)
                base.component(usage="for.test")

    def test_component_specific_model(self):
        """Use component(usage=...) when more than one component match but
        only one for the specific model"""
        # we create a new Component with _usage 'for.test', in the same
        # collection and no _apply_on. This is a generic component for the
        # collection
        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            # When a component has no _apply_on, it means it can be applied on
            # *any* model. Here, the candidates components would be:
            # component1 # (because we are working with res.partner),
            # component3 (because it # has no _apply_on so apply in any case).
            # When a component is specifically linked to a model with
            # _apply_on, it takes precedence over a generic component. It
            # allows to create a generic implementation (component3 here) and
            # override it only for a given model. So in this case, the final
            # component is component1.
            comp = base.component(usage="for.test")
            self.assertEqual("component1", comp._name)

    def test_component_specific_collection(self):
        """Use component(usage=...) when more than one component match but
        only one for the specific collection"""
        # we create a new Component with _usage 'for.test', without collection
        # and no _apply_on
        class Component3(Component):
            _name = "component3"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            # When a component has no _apply_on, it means it can be applied
            # on *any* model. Here, the candidates components would be:
            # component1 (because we are working with res.partner),
            # component3 (because it has no _apply_on so apply in any case).
            # When a component has no _collection, it means it can be applied
            # on all model if no component is found for the current collection:
            # component3 must be ignored since a component (component1) exists
            # and is specificaly linked to the expected collection.
            comp = base.component(usage="for.test")
            self.assertEqual("component1", comp._name)

    def test_component_specific_collection_specific_model(self):
        """Use component(usage=...) when more than one component match but
        only one for the specific model and collection"""
        # we create a new Component with _usage 'for.test', without collection
        # and no _apply_on. This is a component generic for all collections and
        # models
        class Component3(Component):
            _name = "component3"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            # When a component has no _apply_on, it means it can be applied on
            # *any* model, no _collection, it can be applied on *any*
            # collection.
            # Here, the candidates components would be:
            # component1 (because we are working with res.partner),
            # component3 (because it has no _apply_on and no _collection so
            # apply in any case).
            # When a component is specifically linked to a model with
            # _apply_on, it takes precedence over a generic component, the same
            # happens for collection. It allows to create a generic
            # implementation (component3 here) and override it only for a given
            # collection and model. So in this case, the final component is
            # component1.
            comp = base.component(usage="for.test")
            self.assertEqual("component1", comp._name)

    def test_many_components(self):
        """Use many_components(usage=...) on the same model"""

        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            comps = base.many_components(usage="for.test")

        # When a component has no _apply_on, it means it can be applied
        # on *any* model. So here, both component1 and component3 match
        self.assertEqual(["component1", "component3"], [c._name for c in comps])

    def test_many_components_other_model(self):
        """Use many_components(usage=...) on a different model (name)"""

        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _apply_on = "res.users"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            comps = base.many_components(usage="for.test", model_name="res.users")

        self.assertEqual(["component2", "component3"], [c._name for c in comps])

    def test_many_components_other_model_env(self):
        """Use many_components(usage=...) on a different model (instance)"""

        class Component3(Component):
            _name = "component3"
            _collection = "collection.base"
            _apply_on = "res.users"
            _usage = "for.test"

        Component3._build_component(self.comp_registry)

        with self.get_base() as base:
            comps = base.many_components(
                usage="for.test", model_name=self.env["res.users"]
            )

        self.assertEqual(["component2", "component3"], [c._name for c in comps])

    def test_no_component(self):
        """No component found for asked usage"""
        with self.get_base() as base:
            with self.assertRaises(NoComponentError):
                base.component(usage="foo")

    def test_no_many_component(self):
        """No component found for asked usage for many_components()"""
        with self.get_base() as base:
            self.assertEqual([], base.many_components(usage="foo"))

    def test_work_on_component(self):
        """Check WorkContext.component() (shortcut to Component.component)"""
        with self.get_base() as base:
            comp = base.work.component(usage="for.test")
            self.assertEqual("component1", comp._name)

    def test_work_on_many_components(self):
        """Check WorkContext.many_components()

        (shortcut to Component.many_components)
        """
        with self.get_base() as base:
            comps = base.work.many_components(usage="for.test")
            self.assertEqual("component1", comps[0]._name)

    def test_component_match(self):
        """Lookup with match method"""

        class Foo(Component):
            _name = "foo"
            _collection = "collection.base"
            _usage = "speaker"
            _apply_on = ["res.partner"]

            @classmethod
            def _component_match(cls, work, **kw):
                return False

        class Bar(Component):
            _name = "bar"
            _collection = "collection.base"
            _usage = "speaker"
            _apply_on = ["res.partner"]

        self._build_components(Foo, Bar)

        with self.get_base() as base:
            # both components would we returned without the
            # _component_match method
            comp = base.component(usage="speaker", model_name=self.env["res.partner"])
            self.assertEqual("bar", comp._name)
