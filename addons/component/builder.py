# Copyright 2019 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""

Components Builder
==================

Build the components at the build of a registry.

"""
import odoo
from odoo import models

from .core import DEFAULT_CACHE_SIZE, ComponentRegistry, _component_databases


class ComponentBuilder(models.AbstractModel):
    """Build the component classes

    And register them in a global registry.

    Every time an Odoo registry is built, the know components are cleared and
    rebuilt as well.  The Component classes are built using the same mechanism
    than Odoo's Models: a final class is created, taking every Components with
    a ``_name`` and applying Components with an ``_inherits`` upon them.

    The final Component classes are registered in global registry.

    This class is an Odoo model, allowing us to hook the build of the
    components at the end of the Odoo's registry loading, using
    ``_register_hook``. This method is called after all modules are loaded, so
    we are sure that we have all the components Classes and in the correct
    order.

    """

    _name = "component.builder"
    _description = "Component Builder"

    _components_registry_cache_size = DEFAULT_CACHE_SIZE

    def _register_hook(self):
        # This method is called by Odoo when the registry is built,
        # so in case the registry is rebuilt (cache invalidation, ...),
        # we have to to rebuild the components. We use a new
        # registry so we have an empty cache and we'll add components in it.
        components_registry = self._init_global_registry()
        self.build_registry(components_registry)
        components_registry.ready = True

    def _init_global_registry(self):
        components_registry = ComponentRegistry(
            cachesize=self._components_registry_cache_size
        )
        _component_databases[self.env.cr.dbname] = components_registry
        return components_registry

    def build_registry(self, components_registry, states=None, exclude_addons=None):
        if not states:
            states = ("installed", "to upgrade")
        # lookup all the installed (or about to be) addons and generate
        # the graph, so we can load the components following the order
        # of the addons' dependencies
        graph = odoo.modules.graph.Graph()
        graph.add_module(self.env.cr, "base")

        query = "SELECT name " "FROM ir_module_module " "WHERE state IN %s "
        params = [tuple(states)]
        if exclude_addons:
            query += " AND name NOT IN %s "
            params.append(tuple(exclude_addons))
        self.env.cr.execute(query, params)

        module_list = [name for (name,) in self.env.cr.fetchall() if name not in graph]
        graph.add_modules(self.env.cr, module_list)

        for module in graph:
            self.load_components(module.name, components_registry=components_registry)

    def load_components(self, module, components_registry=None):
        """Build every component known by MetaComponent for an odoo module

        The final component (composed by all the Component classes in this
        module) will be pushed into the registry.

        :param module: the name of the addon for which we want to load
                       the components
        :type module: str | unicode
        :param registry: the registry in which we want to put the Component
        :type registry: :py:class:`~.core.ComponentRegistry`
        """
        components_registry = (
            components_registry or _component_databases[self.env.cr.dbname]
        )
        components_registry.load_components(module)
