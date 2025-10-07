# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

# Tell pylint to not bother us for all our fake component classes
# pylint: disable=consider-merging-classes-inherited

from unittest import mock

from odoo.addons.component.core import AbstractComponent, Component

from .common import TransactionComponentRegistryCase


class TestBuildComponent(TransactionComponentRegistryCase):
    """Test build of components

    All the tests in this suite are based on the same principle with
    variations:

    * Create new Components (classes inheriting from
      :class:`component.core.Component` or
      :class:`component.core.AbstractComponent`
    * Call :meth:`component.core.Component._build_component` on them
      in order to build the 'final class' composed from all the ``_inherit``
      and push it in the components registry (``self.comp_registry`` here)
    * Assert that classes are built, registered, have correct ``__bases__``...

    """

    def setUp(self):
        super().setUp()
        self._setup_registry(self)

    def tearDown(self):
        self._teardown_registry(self)
        super().tearDown()

    def test_no_name(self):
        """Ensure that a component has a _name"""

        class Component1(Component):
            pass

        msg = ".*must have a _name.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component1._build_component(self.comp_registry)

    def test_register(self):
        """Able to register components in components registry"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _name = "component2"

        # build the 'final classes' for the components and check that we find
        # them in the components registry
        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        self.assertEqual(["base", "component1", "component2"], list(self.comp_registry))

    def test_inherit_bases(self):
        """Check __bases__ of Component with _inherit"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _inherit = "component1"

        class Component3(Component):
            _inherit = "component1"

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        Component3._build_component(self.comp_registry)
        self.assertEqual(
            (Component3, Component2, Component1, self.comp_registry["base"]),
            self.comp_registry["component1"].__bases__,
        )

    def test_prototype_inherit_bases(self):
        """Check __bases__ of Component with _inherit and different _name"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _name = "component2"
            _inherit = "component1"

        class Component3(Component):
            _name = "component3"
            _inherit = "component1"

        class Component4(Component):
            _name = "component4"
            _inherit = ["component2", "component3"]

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        Component3._build_component(self.comp_registry)
        Component4._build_component(self.comp_registry)
        self.assertEqual(
            (Component1, self.comp_registry["base"]),
            self.comp_registry["component1"].__bases__,
        )
        self.assertEqual(
            (Component2, self.comp_registry["component1"], self.comp_registry["base"]),
            self.comp_registry["component2"].__bases__,
        )
        self.assertEqual(
            (Component3, self.comp_registry["component1"], self.comp_registry["base"]),
            self.comp_registry["component3"].__bases__,
        )
        self.assertEqual(
            (
                Component4,
                self.comp_registry["component2"],
                self.comp_registry["component3"],
                self.comp_registry["base"],
            ),
            self.comp_registry["component4"].__bases__,
        )

    # pylint: disable=W8110
    def test_custom_build(self):
        """Check that we can hook at the end of a Component build"""

        class Component1(Component):
            _name = "component1"

            @classmethod
            def _complete_component_build(cls):
                # This method should be called after the Component
                # is built, and before it is pushed in the registry
                cls._build_done = True

        Component1._build_component(self.comp_registry)
        # we inspect that our custom build has been executed
        self.assertTrue(self.comp_registry["component1"]._build_done)

    def test_inherit_attrs(self):
        """Check attributes inheritance of Components with _inherit"""

        class Component1(Component):
            _name = "component1"

            msg = "ping"

            def say(self):
                return "foo"

        class Component2(Component):
            _name = "component2"
            _inherit = "component1"

            msg = "pong"

            def say(self):
                return super().say() + " bar"

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        # we initialize the components, normally we should pass
        # an instance of WorkContext, but we don't need a real one
        # for this test
        component1 = self.comp_registry["component1"](mock.Mock())
        component2 = self.comp_registry["component2"](mock.Mock())
        self.assertEqual("ping", component1.msg)
        self.assertEqual("pong", component2.msg)
        self.assertEqual("foo", component1.say())
        self.assertEqual("foo bar", component2.say())

    def test_duplicate_component(self):
        """Check that we can't have 2 components with the same name"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _name = "component1"

        Component1._build_component(self.comp_registry)
        msg = "Component.*already exists.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component2._build_component(self.comp_registry)

    def test_no_parent(self):
        """Ensure we can't _inherit a non-existent component"""

        class Component1(Component):
            _name = "component1"
            _inherit = "component1"

        msg = "Component.*does not exist in registry.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component1._build_component(self.comp_registry)

    def test_no_parent2(self):
        """Ensure we can't _inherit by prototype a non-existent component"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _name = "component2"
            _inherit = ["component1", "component3"]

        Component1._build_component(self.comp_registry)
        msg = "Component.*inherits from non-existing component.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component2._build_component(self.comp_registry)

    def test_add_inheritance(self):
        """Ensure we can add a new inheritance"""

        class Component1(Component):
            _name = "component1"

        class Component2(Component):
            _name = "component2"

        class Component2bis(Component):
            _name = "component2"
            _inherit = ["component2", "component1"]

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        Component2bis._build_component(self.comp_registry)

        self.assertEqual(
            (
                Component2bis,
                Component2,
                self.comp_registry["component1"],
                self.comp_registry["base"],
            ),
            self.comp_registry["component2"].__bases__,
        )

    def test_check_parent_component_over_abstract(self):
        """Component can inherit from AbstractComponent"""

        class Component1(AbstractComponent):
            _name = "component1"

        class Component2(Component):
            _name = "component2"
            _inherit = "component1"

        Component1._build_component(self.comp_registry)
        Component2._build_component(self.comp_registry)
        self.assertTrue(self.comp_registry["component1"]._abstract)
        self.assertFalse(self.comp_registry["component2"]._abstract)

    def test_check_parent_abstract_over_component(self):
        """Prevent AbstractComponent to inherit from Component"""

        class Component1(Component):
            _name = "component1"

        class Component2(AbstractComponent):
            _name = "component2"
            _inherit = "component1"

        Component1._build_component(self.comp_registry)
        msg = ".*cannot inherit from the non-abstract.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component2._build_component(self.comp_registry)

    def test_check_transform_abstract_to_component(self):
        """Prevent AbstractComponent to be transformed to Component"""

        class Component1(AbstractComponent):
            _name = "component1"

        class Component1bis(Component):
            _inherit = "component1"

        Component1._build_component(self.comp_registry)
        msg = ".*transforms the abstract component.*into a non-abstract.*"
        with self.assertRaisesRegex(TypeError, msg):
            Component1bis._build_component(self.comp_registry)
