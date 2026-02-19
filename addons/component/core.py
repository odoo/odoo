# Copyright 2017 Camptocamp SA
# Copyright 2017 Odoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""

Core
====

Core classes for the components.
The most common classes used publicly are:

* :class:`Component`
* :class:`AbstractComponent`
* :class:`WorkContext`

"""

import logging
import operator
from collections import OrderedDict, defaultdict

from odoo import models
from odoo.tools import LastOrderedSet, OrderedSet

from .exception import NoComponentError, RegistryNotReadyError, SeveralComponentError

_logger = logging.getLogger(__name__)

try:
    from cachetools import LRUCache, cachedmethod
except ImportError:
    _logger.debug("Cannot import 'cachetools'.")


# The Cache size represents the number of items, so the number
# of components (include abstract components) we will keep in the LRU
# cache. We would need stats to know what is the average but this is a bit
# early.
DEFAULT_CACHE_SIZE = 512


# this is duplicated from odoo.models.MetaModel._get_addon_name() which we
# unfortunately can't use because it's an instance method and should have been
# a @staticmethod
def _get_addon_name(full_name):
    # The (Odoo) module name can be in the ``odoo.addons`` namespace
    # or not. For instance, module ``sale`` can be imported as
    # ``odoo.addons.sale`` (the right way) or ``sale`` (for backward
    # compatibility).
    module_parts = full_name.split(".")
    if len(module_parts) > 2 and module_parts[:2] == ["odoo", "addons"]:
        addon_name = full_name.split(".")[2]
    else:
        addon_name = full_name.split(".")[0]
    return addon_name


class ComponentDatabases(dict):
    """Holds a registry of components for each database"""


class ComponentRegistry:
    """Store all the components and allow to find them using criteria

    The key is the ``_name`` of the components.

    This is an OrderedDict, because we want to keep the registration order of
    the components, addons loaded first have their components found first.

    The :attr:`ready` attribute must be set to ``True`` when all the components
    are loaded.

    """

    def __init__(self, cachesize=DEFAULT_CACHE_SIZE):
        self._cache = LRUCache(maxsize=cachesize)
        self._components = OrderedDict()
        self._loaded_modules = set()
        self.ready = False

    def __getitem__(self, key):
        return self._components[key]

    def __setitem__(self, key, value):
        self._components[key] = value

    def __contains__(self, key):
        return key in self._components

    def get(self, key, default=None):
        return self._components.get(key, default)

    def __iter__(self):
        return iter(self._components)

    def load_components(self, module):
        if module in self._loaded_modules:
            return
        for component_class in MetaComponent._modules_components[module]:
            component_class._build_component(self)
        self._loaded_modules.add(module)

    @cachedmethod(operator.attrgetter("_cache"))
    def lookup(self, collection_name=None, usage=None, model_name=None):
        """Find and return a list of components for a usage

        If a component is not registered in a particular collection (no
        ``_collection``), it will be returned in any case (as far as
        the ``usage`` and ``model_name`` match).  This is useful to share
        generic components across different collections.

        If no collection name is given, components from any collection
        will be returned.

        Then, the components of a collection are filtered by usage and/or
        model. The ``_usage`` is mandatory on the components. When the
        ``_model_name`` is empty, it means it can be used for every models,
        and it will ignore the ``model_name`` argument.

        The abstract components are never returned.

        This is a rather low-level function, usually you will use the
        high-level :meth:`AbstractComponent.component`,
        :meth:`AbstractComponent.many_components` or even
        :meth:`AbstractComponent.component_by_name`.

        :param collection_name: the name of the collection the component is
                                registered into.
        :param usage: the usage of component we are looking for
        :param model_name: filter on components that apply on this model

        """

        # keep the order so addons loaded first have components used first
        candidates = (
            component
            for component in self._components.values()
            if not component._abstract
        )

        if collection_name is not None:
            candidates = (
                component
                for component in candidates
                if (
                    component._collection == collection_name
                    or component._collection is None
                )
            )

        if usage is not None:
            candidates = (
                component for component in candidates if component._usage == usage
            )

        if model_name is not None:
            candidates = (
                c
                for c in candidates
                if c.apply_on_models is None or model_name in c.apply_on_models
            )

        return list(candidates)


# We will store a ComponentRegistry per database here,
# it will be cleared and updated when the odoo's registry is rebuilt
_component_databases = ComponentDatabases()


class WorkContext:
    """Transport the context required to work with components

    It is propagated through all the components, so any
    data or instance (like a random RPC client) that need
    to be propagated transversally to the components
    should be kept here.

    Including:

    .. attribute:: model_name

        Name of the model we are working with. It means that any lookup for a
        component will be done for this model. It also provides a shortcut
        as a `model` attribute to use directly with the Odoo model from
        the components

    .. attribute:: collection

        The collection we are working with. The collection is an Odoo
        Model that inherit from 'collection.base'. The collection attribute
        can be a record or an "empty" model.

    .. attribute:: model

        Odoo Model for ``model_name`` with the same Odoo
        :class:`~odoo.api.Environment` than the ``collection`` attribute.

    This is also the entrypoint to work with the components.

    ::

        collection = self.env['my.collection'].browse(1)
        work = WorkContext(model_name='res.partner', collection=collection)
        component = work.component(usage='record.importer')

    Usually you will use the context manager on the ``collection.base`` Model:

    ::

        collection = self.env['my.collection'].browse(1)
        with collection.work_on('res.partner') as work:
            component = work.component(usage='record.importer')

    It supports any arbitrary keyword arguments that will become attributes of
    the instance, and be propagated throughout all the components.

    ::

        collection = self.env['my.collection'].browse(1)
        with collection.work_on('res.partner', hello='world') as work:
            assert work.hello == 'world'

    When you need to work on a different model, a new work instance will be
    created for you when you are using the high-level API. This is what
    happens under the hood:

    ::

        collection = self.env['my.collection'].browse(1)
        with collection.work_on('res.partner', hello='world') as work:
            assert work.model_name == 'res.partner'
            assert work.hello == 'world'
            work2 = work.work_on('res.users')
            # => spawn a new WorkContext with a copy of the attributes
            assert work2.model_name == 'res.users'
            assert work2.hello == 'world'

    """

    def __init__(
        self, model_name=None, collection=None, components_registry=None, **kwargs
    ):
        self.collection = collection
        self.model_name = model_name
        self.model = self.env[model_name]
        # lookup components in an alternative registry, used by the tests
        if components_registry is not None:
            self.components_registry = components_registry
        else:
            dbname = self.env.cr.dbname
            try:
                self.components_registry = _component_databases[dbname]
            except KeyError as exc:
                msg = (
                    "No component registry for database %s. "
                    "Probably because the Odoo registry has not been built "
                    "yet."
                )
                _logger.error(
                    msg,
                    dbname,
                )
                raise RegistryNotReadyError(msg) from exc
        self._propagate_kwargs = ["collection", "model_name", "components_registry"]
        for attr_name, value in kwargs.items():
            setattr(self, attr_name, value)
            self._propagate_kwargs.append(attr_name)

    @property
    def env(self):
        """Return the current Odoo env

        This is the environment of the current collection.
        """
        return self.collection.env

    def work_on(self, model_name=None, collection=None):
        """Create a new work context for another model keeping attributes

        Used when one need to lookup components for another model.
        """
        kwargs = {
            attr_name: getattr(self, attr_name) for attr_name in self._propagate_kwargs
        }
        if collection is not None:
            kwargs["collection"] = collection
        if model_name is not None:
            kwargs["model_name"] = model_name
        return self.__class__(**kwargs)

    def _component_class_by_name(self, name):
        components_registry = self.components_registry
        component_class = components_registry.get(name)
        if not component_class:
            raise NoComponentError("No component with name '%s' found." % name)
        return component_class

    def component_by_name(self, name, model_name=None):
        """Return a component by its name

        If the component exists, an instance of it will be returned,
        initialized with the current :class:`WorkContext`.

        A :exc:`odoo.addons.component.exception.NoComponentError` is raised
        if:

        * no component with this name exists
        * the ``_apply_on`` of the found component does not match
          with the current working model

        In the latter case, it can be an indication that you need to switch to
        a different model, you can do so by providing the ``model_name``
        argument.

        """
        if isinstance(model_name, models.BaseModel):
            model_name = model_name._name
        component_class = self._component_class_by_name(name)
        work_model = model_name or self.model_name
        if (
            component_class._collection
            and self.collection._name != component_class._collection
        ):
            raise NoComponentError(
                "Component with name '%s' can't be used for collection '%s'."
                % (name, self.collection._name)
            )

        if (
            component_class.apply_on_models
            and work_model not in component_class.apply_on_models
        ):
            if len(component_class.apply_on_models) == 1:
                hint_models = "'{}'".format(component_class.apply_on_models[0])
            else:
                hint_models = "<one of {!r}>".format(component_class.apply_on_models)
            raise NoComponentError(
                "Component with name '%s' can't be used for model '%s'.\n"
                "Hint: you might want to use: "
                "component_by_name('%s', model_name=%s)"
                % (name, work_model, name, hint_models)
            )

        if work_model == self.model_name:
            work_context = self
        else:
            work_context = self.work_on(model_name)
        return component_class(work_context)

    def _lookup_components(self, usage=None, model_name=None, **kw):
        component_classes = self.components_registry.lookup(
            self.collection._name, usage=usage, model_name=model_name
        )
        matching_components = []
        for cls in component_classes:
            try:
                matching = cls._component_match(
                    self, usage=usage, model_name=model_name, **kw
                )
            except TypeError as err:
                # Backward compat
                _logger.info(str(err))
                _logger.info(
                    "The signature of %s._component_match has changed. "
                    "Please, adapt your code as "
                    "(self, usage=usage, model_name=model_name, **kw)",
                    cls.__name__,
                )
                matching = cls._component_match(self)
            if matching:
                matching_components.append(cls)
        return matching_components

    def _filter_components_by_collection(self, component_classes):
        return [c for c in component_classes if c._collection == self.collection._name]

    def _filter_components_by_model(self, component_classes, model_name):
        return [
            c
            for c in component_classes
            if c.apply_on_models and model_name in c.apply_on_models
        ]

    def _ensure_model_name(self, model_name):
        """Make sure model name is a string or fallback to current ctx value."""
        if isinstance(model_name, models.BaseModel):
            model_name = model_name._name
        return model_name or self.model_name

    def _matching_components(self, usage=None, model_name=None, **kw):
        """Retrieve matching components and their work context."""
        component_classes = self._lookup_components(
            usage=usage, model_name=model_name, **kw
        )
        if model_name == self.model_name:
            work_context = self
        else:
            work_context = self.work_on(model_name)
        return component_classes, work_context

    def component(self, usage=None, model_name=None, **kw):
        """Find a component by usage and model for the current collection

        It searches a component using the rules of
        :meth:`ComponentRegistry.lookup`. When a component is found,
        it initialize it with the current :class:`WorkContext` and returned.

        A component with a ``_apply_on`` matching the asked ``model_name``
        takes precedence over a generic component without ``_apply_on``.
        A component with a ``_collection`` matching the current collection
        takes precedence over a generic component without ``_collection``.
        This behavior allows to define generic components across collections
        and/or models and override them only for a particular collection and/or
        model.

        A :exc:`odoo.addons.component.exception.SeveralComponentError` is
        raised if more than one component match for the provided
        ``usage``/``model_name``.

        A :exc:`odoo.addons.component.exception.NoComponentError` is raised
        if no component is found for the provided ``usage``/``model_name``.

        """
        model_name = self._ensure_model_name(model_name)
        component_classes, work_context = self._matching_components(
            usage=usage, model_name=model_name, **kw
        )
        if not component_classes:
            raise NoComponentError(
                "No component found for collection '%s', "
                "usage '%s', model_name '%s'."
                % (self.collection._name, usage, model_name)
            )
        elif len(component_classes) > 1:
            # If we have more than one component, try to find the one
            # specifically linked to the collection...
            component_classes = self._filter_components_by_collection(component_classes)
        if len(component_classes) > 1:
            # ... or try to find the one specifically linked to the model
            component_classes = self._filter_components_by_model(
                component_classes, model_name
            )
        if len(component_classes) != 1:
            raise SeveralComponentError(
                "Several components found for collection '%s', "
                "usage '%s', model_name '%s'. Found: %r"
                % (
                    self.collection._name,
                    usage or "",
                    model_name or "",
                    component_classes,
                )
            )
        return component_classes[0](work_context)

    def many_components(self, usage=None, model_name=None, **kw):
        """Find many components by usage and model for the current collection

        It searches a component using the rules of
        :meth:`ComponentRegistry.lookup`. When components are found, they
        initialized with the current :class:`WorkContext` and returned as a
        list.

        If no component is found, an empty list is returned.

        """
        model_name = self._ensure_model_name(model_name)
        component_classes, work_context = self._matching_components(
            usage=usage, model_name=model_name, **kw
        )
        return [comp(work_context) for comp in component_classes]

    def __str__(self):
        return "WorkContext({}, {})".format(self.model_name, repr(self.collection))

    __repr__ = __str__


class MetaComponent(type):
    """Metaclass for Components

    Every new :class:`Component` will be added to ``_modules_components``,
    that will be used by the component builder.

    """

    _modules_components = defaultdict(list)

    def __init__(cls, name, bases, attrs):
        if not cls._register:
            cls._register = True
            super().__init__(name, bases, attrs)
            return

        # If components are declared in tests, exclude them from the
        # "components of the addon" list. If not, when we use the
        # "load_components" method, all the test components would be loaded.
        # This should never be an issue when running the app normally, as the
        # Python tests should never be executed. But this is an issue when a
        # test creates a test components for the purpose of the test, then a
        # second tests uses the "load_components" to load all the addons of the
        # module: it will load the component of the previous test.
        if "tests" in cls.__module__.split("."):
            return

        if not hasattr(cls, "_module"):
            cls._module = _get_addon_name(cls.__module__)

        cls._modules_components[cls._module].append(cls)

    @property
    def apply_on_models(cls):
        # None means all models
        if cls._apply_on is None:
            return None
        # always return a list, used for the lookup
        elif isinstance(cls._apply_on, str):
            return [cls._apply_on]
        return cls._apply_on


class AbstractComponent(metaclass=MetaComponent):
    """Main Component Model

    All components have a Python inheritance either on
    :class:`AbstractComponent` or either on :class:`Component`.

    Abstract Components will not be returned by lookups on components, however
    they can be used as a base for other Components through inheritance (using
    ``_inherit``).

    Inheritance mechanism
        The inheritance mechanism is like the Odoo's one for Models.  Each
        component has a ``_name``. This is the absolute minimum in a Component
        class.

        ::

            class MyComponent(Component):
                _name = 'my.component'

                def speak(self, message):
                    print message

        Every component implicitly inherit from the `'base'` component.

        There are two close but distinct inheritance types, which look
        familiar if you already know Odoo.  The first uses ``_inherit`` with
        an existing name, the name of the component we want to extend.  With
        the following example, ``my.component`` is now able to speak and to
        yell.

        ::

            class MyComponent(Component):  # name of the class does not matter
                _inherit = 'my.component'

                def yell(self, message):
                    print message.upper()

        The second has a different ``_name``, it creates a new component,
        including the behavior of the inherited component, but without
        modifying it. In the following example, ``my.component`` is still able
        to speak and to yell (brough by the previous inherit), but not to
        sing.  ``another.component`` is able to speak, to yell and to sing.

        ::

            class AnotherComponent(Component):
                _name = 'another.component'
                _inherit = 'my.component'

                def sing(self, message):
                    print message.upper()

    Registration and lookups
        It is handled by 3 attributes on the class:

        _collection
            The name of the collection where we want to register the
            component.  This is not strictly mandatory as a component can be
            shared across several collections. But usually, you want to set a
            collection to segregate the components for a domain.  A collection
            can be for instance ``magento.backend``. It is also the name of a
            model that inherits from ``collection.base``.  See also
            :class:`~WorkContext` and
            :class:`~odoo.addons.component.models.collection.Collection`.

        _apply_on
            List of names or name of the Odoo model(s) for which the component
            can be used.  When not set, the component can be used on any model.

        _usage
           The collection and the model (``_apply_on``) will help to filter
           the candidate components according to our working context (e.g. I'm
           working on ``magento.backend`` with the model
           ``magento.res.partner``).  The usage will define **what** kind of
           task the component we are looking for serves to. For instance, it
           might be ``record.importer``, ``export.mapper```... but you can be
           as creative as you want.

        Now, to get a component, you'll likely use
        :meth:`WorkContext.component` when you start to work with components
        in your flow, but then from within your components, you are more
        likely to use one of:

        * :meth:`component`
        * :meth:`many_components`
        * :meth:`component_by_name` (more rarely though)

        Declaration of some Components can look like::

            class FooBar(models.Model):
                _name = 'foo.bar.collection'
                _inherit = 'collection.base'  # this inherit is required


            class FooBarBase(AbstractComponent):
                _name = 'foo.bar.base'
                _collection = 'foo.bar.collection'  # name of the model above


            class Foo(Component):
                _name = 'foo'
                _inherit = 'foo.bar.base'  # we will inherit the _collection
                _apply_on = 'res.users'
                _usage = 'speak'

                def utter(self, message):
                    print message


            class Bar(Component):
                _name = 'bar'
                _inherit = 'foo.bar.base'  # we will inherit the _collection
                _apply_on = 'res.users'
                _usage = 'yell'

                def utter(self, message):
                    print message.upper() + '!!!'


            class Vocalizer(Component):
                _name = 'vocalizer'
                _inherit = 'foo.bar.base'
                _usage = 'vocalizer'
                # can be used for any model

                def vocalize(action, message):
                    self.component(usage=action).utter(message)


        And their usage::

            >>> coll = self.env['foo.bar.collection'].browse(1)
            >>> with coll.work_on('res.users') as work:
            ...     vocalizer = work.component(usage='vocalizer')
            ...     vocalizer.vocalize('speak', 'hello world')
            ...
            hello world
            ...     vocalizer.vocalize('yell', 'hello world')
            HELLO WORLD!!!

    Hints:

    * If you want to create components without ``_apply_on``, choose a
      ``_usage`` that will not conflict other existing components.
    * Unless this is what you want and in that case you use
      :meth:`many_components` which will return all components for a usage
      with a matching or a not set ``_apply_on``.
    * It is advised to namespace the names of the components (e.g.
      ``magento.xxx``) to prevent conflicts between addons.

    """

    _register = False
    _abstract = True

    # used for inheritance
    _name = None  #: Name of the component

    #: Name or list of names of the component(s) to inherit from
    _inherit = None

    #: name of the collection to subscribe in
    _collection = None

    #: List of models on which the component can be applied.
    #: None means any Model, can be a list ['res.users', ...]
    _apply_on = None

    #: Component purpose ('import.mapper', ...).
    _usage = None

    def __init__(self, work_context):
        super().__init__()
        self.work = work_context

    @classmethod
    def _component_match(cls, work, usage=None, model_name=None, **kw):
        """Evaluated on candidate components

        When a component lookup is done and candidate(s) have
        been found for a usage, a final call is done on this method.
        If the method return False, the candidate component is ignored.

        It can be used for instance to dynamically choose a component
        according to a value in the :class:`WorkContext`.

        Beware, if the lookups from usage, model and collection are
        cached, the calls to :meth:`_component_match` are executed
        each time we get components. Heavy computation should be
        avoided.

        :param work: the :class:`WorkContext` we are working with

        """
        return True

    @property
    def collection(self):
        """Collection we are working with"""
        return self.work.collection

    @property
    def env(self):
        """Current Odoo environment, the one of the collection record"""
        return self.work.env

    @property
    def model(self):
        """The model instance we are working with"""
        return self.work.model

    def component_by_name(self, name, model_name=None):
        """Return a component by its name

        Shortcut to meth:`~WorkContext.component_by_name`
        """
        return self.work.component_by_name(name, model_name=model_name)

    def component(self, usage=None, model_name=None, **kw):
        """Return a component

        Shortcut to meth:`~WorkContext.component`
        """
        return self.work.component(usage=usage, model_name=model_name, **kw)

    def many_components(self, usage=None, model_name=None, **kw):
        """Return several components

        Shortcut to meth:`~WorkContext.many_components`
        """
        return self.work.many_components(usage=usage, model_name=model_name, **kw)

    def __str__(self):
        return "Component(%s)" % self._name

    __repr__ = __str__

    @classmethod
    def _build_component(cls, registry):
        """Instantiate a given Component in the components registry.

        This method is called at the end of the Odoo's registry build.  The
        caller is :meth:`component.builder.ComponentBuilder.load_components`.

        It generates new classes, which will be the Component classes we will
        be using.  The new classes are generated following the inheritance
        of ``_inherit``. It ensures that the ``__bases__`` of the generated
        Component classes follow the ``_inherit`` chain.

        Once a Component class is created, it adds it in the Component Registry
        (:class:`ComponentRegistry`), so it will be available for
        lookups.

        At the end of new class creation, a hook method
        :meth:`_complete_component_build` is called, so you can customize
        further the created components. An example can be found in
        :meth:`odoo.addons.connector.components.mapper.Mapper._complete_component_build`

        The following code is roughly the same than the Odoo's one for
        building Models.

        """

        # In the simplest case, the component's registry class inherits from
        # cls and the other classes that define the component in a flat
        # hierarchy.  The registry contains the instance ``component`` (on the
        # left). Its class, ``ComponentClass``, carries inferred metadata that
        # is shared between all the component's instances for this registry
        # only.
        #
        #   class A1(Component):                    Component
        #       _name = 'a'                           / | \
        #                                            A3 A2 A1
        #   class A2(Component):                      \ | /
        #       _inherit = 'a'                    ComponentClass
        #
        #   class A3(Component):
        #       _inherit = 'a'
        #
        # When a component is extended by '_inherit', its base classes are
        # modified to include the current class and the other inherited
        # component classes.
        # Note that we actually inherit from other ``ComponentClass``, so that
        # extensions to an inherited component are immediately visible in the
        # current component class, like in the following example:
        #
        #   class A1(Component):
        #       _name = 'a'                          Component
        #                                            /  / \  \
        #   class B1(Component):                    /  A2 A1  \
        #       _name = 'b'                        /   \  /    \
        #                                         B2 ComponentA B1
        #   class B2(Component):                   \     |     /
        #       _name = 'b'                         \    |    /
        #       _inherit = ['b', 'a']                \   |   /
        #                                            ComponentB
        #   class A2(Component):
        #       _inherit = 'a'

        # determine inherited components
        parents = cls._inherit
        if isinstance(parents, str):
            parents = [parents]
        elif parents is None:
            parents = []

        if cls._name in registry and not parents:
            raise TypeError(
                "Component %r (in class %r) already exists. "
                "Consider using _inherit instead of _name "
                "or using a different _name." % (cls._name, cls)
            )

        # determine the component's name
        name = cls._name or (len(parents) == 1 and parents[0])

        if not name:
            raise TypeError("Component %r must have a _name" % cls)

        # all components except 'base' implicitly inherit from 'base'
        if name != "base":
            parents = list(parents) + ["base"]

        # create or retrieve the component's class
        if name in parents:
            if name not in registry:
                raise TypeError("Component %r does not exist in registry." % name)
            ComponentClass = registry[name]
            ComponentClass._build_component_check_base(cls)
            check_parent = ComponentClass._build_component_check_parent
        else:
            ComponentClass = type(
                name,
                (AbstractComponent,),
                {
                    "_name": name,
                    "_register": False,
                    # names of children component
                    "_inherit_children": OrderedSet(),
                },
            )
            check_parent = cls._build_component_check_parent

        # determine all the classes the component should inherit from
        bases = LastOrderedSet([cls])
        for parent in parents:
            if parent not in registry:
                raise TypeError(
                    "Component %r inherits from non-existing component %r."
                    % (name, parent)
                )
            parent_class = registry[parent]
            if parent == name:
                for base in parent_class.__bases__:
                    bases.add(base)
            else:
                check_parent(cls, parent_class)
                bases.add(parent_class)
                parent_class._inherit_children.add(name)
        ComponentClass.__bases__ = tuple(bases)

        ComponentClass._complete_component_build()

        registry[name] = ComponentClass

        return ComponentClass

    @classmethod
    def _build_component_check_base(cls, extend_cls):
        """Check whether ``cls`` can be extended with ``extend_cls``."""
        if cls._abstract and not extend_cls._abstract:
            msg = (
                "%s transforms the abstract component %r into a "
                "non-abstract component. "
                "That class should either inherit from AbstractComponent, "
                "or set a different '_name'."
            )
            raise TypeError(msg % (extend_cls, cls._name))

    @classmethod
    def _build_component_check_parent(component_class, cls, parent_class):  # noqa: B902
        """Check whether ``model_class`` can inherit from ``parent_class``."""
        if component_class._abstract and not parent_class._abstract:
            msg = (
                "In %s, the abstract Component %r cannot inherit "
                "from the non-abstract Component %r."
            )
            raise TypeError(msg % (cls, component_class._name, parent_class._name))

    @classmethod
    def _complete_component_build(cls):
        """Complete build of the new component class

        After the component has been built from its bases, this method is
        called, and can be used to customize the class before it can be used.

        Nothing is done in the base Component, but a Component can inherit
        the method to add its own behavior.
        """


class Component(AbstractComponent):
    """Concrete Component class

    This is the class you inherit from when you want your component to
    be registered in the component collections.

    Look in :class:`AbstractComponent` for more details.

    """

    _register = False
    _abstract = False
