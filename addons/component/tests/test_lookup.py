# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.component.core import AbstractComponent, Component

from .common import TransactionComponentRegistryCase


class TestLookup(TransactionComponentRegistryCase):
    """Test the ComponentRegistry

    Tests in this testsuite mainly do:

    * Create new Components (classes inheriting from
      :class:`component.core.Component` or
      :class:`component.core.AbstractComponent`
    * Call :meth:`component.core.Component._build_component` on them
      in order to build the 'final class' composed from all the ``_inherit``
      and push it in the components registry (``self.comp_registry`` here)
    * Use the lookup method of the components registry and check
      that we get the correct result

    """

    def setUp(self):
        super().setUp()
        self._setup_registry(self)

    def tearDown(self):
        self._teardown_registry(self)
        super().tearDown()

    def test_lookup_collection(self):
        """Lookup components of a collection"""
        # we register 2 components in foobar and one in other
        class Foo(Component):
            _name = "foo"
            _collection = "foobar"

        class Bar(Component):
            _name = "bar"
            _collection = "foobar"

        class Homer(Component):
            _name = "homer"
            _collection = "other"

        self._build_components(Foo, Bar, Homer)

        # we should no see the component in 'other'
        components = self.comp_registry.lookup("foobar")
        self.assertEqual(["foo", "bar"], [c._name for c in components])

    def test_lookup_usage(self):
        """Lookup components by usage"""

        class Foo(Component):
            _name = "foo"
            _collection = "foobar"
            _usage = "speaker"

        class Bar(Component):
            _name = "bar"
            _collection = "foobar"
            _usage = "speaker"

        class Baz(Component):
            _name = "baz"
            _collection = "foobar"
            _usage = "listener"

        self._build_components(Foo, Bar, Baz)

        components = self.comp_registry.lookup("foobar", usage="listener")
        self.assertEqual("baz", components[0]._name)

        components = self.comp_registry.lookup("foobar", usage="speaker")
        self.assertEqual(["foo", "bar"], [c._name for c in components])

    def test_lookup_no_component(self):
        """No component"""
        # we just expect an empty list when no component match, the error
        # handling is handled at an higher level
        self.assertEqual([], self.comp_registry.lookup("something", usage="something"))

    def test_get_by_name(self):
        """Get component by name"""

        class Foo(AbstractComponent):
            _name = "foo"
            _collection = "foobar"

        self._build_components(Foo)
        # this is just a dict access
        self.assertEqual("foo", self.comp_registry["foo"]._name)

    def test_lookup_abstract(self):
        """Do not include abstract components in lookup"""

        class Foo(AbstractComponent):
            _name = "foo"
            _collection = "foobar"
            _usage = "speaker"

        class Bar(Component):
            _name = "bar"
            _inherit = "foo"

        self._build_components(Foo, Bar)

        comp_registry = self.comp_registry

        # we should never have 'foo' in the returned components
        # as it is abstract
        components = comp_registry.lookup("foobar", usage="speaker")
        self.assertEqual("bar", components[0]._name)

        components = comp_registry.lookup("foobar", usage="speaker")
        self.assertEqual(["bar"], [c._name for c in components])

    def test_lookup_model_name(self):
        """Lookup with model names"""

        class Foo(Component):
            _name = "foo"
            _collection = "foobar"
            _usage = "speaker"
            # support list
            _apply_on = ["res.partner"]

        class Bar(Component):
            _name = "bar"
            _collection = "foobar"
            _usage = "speaker"
            # support string
            _apply_on = "res.users"

        class Any(Component):
            # can be used with any model as far as we look it up
            # with its usage
            _name = "any"
            _collection = "foobar"
            _usage = "listener"

        self._build_components(Foo, Bar, Any)

        components = self.comp_registry.lookup(
            "foobar", usage="speaker", model_name="res.partner"
        )
        self.assertEqual("foo", components[0]._name)

        components = self.comp_registry.lookup(
            "foobar", usage="speaker", model_name="res.users"
        )
        self.assertEqual("bar", components[0]._name)

        components = self.comp_registry.lookup(
            "foobar", usage="listener", model_name="res.users"
        )
        self.assertEqual("any", components[0]._name)

    def test_lookup_cache(self):
        """Lookup uses a cache"""

        class Foo(Component):
            _name = "foo"
            _collection = "foobar"

        self._build_components(Foo)

        components = self.comp_registry.lookup("foobar")
        self.assertEqual(["foo"], [c._name for c in components])

        # we add a new component
        class Bar(Component):
            _name = "bar"
            _collection = "foobar"

        self._build_components(Bar)

        # As the lookups are cached, we should still see only foo,
        # even if we added a new component.
        # We do this for testing, but in a real use case, we can't
        # add new Component classes on the fly, and when we install
        # new addons, the registry is rebuilt and cache cleared.
        components = self.comp_registry.lookup("foobar")
        self.assertEqual(["foo"], [c._name for c in components])

        self.comp_registry._cache.clear()
        # now we should find them both as the cache has been cleared
        components = self.comp_registry.lookup("foobar")
        self.assertEqual(["foo", "bar"], [c._name for c in components])
