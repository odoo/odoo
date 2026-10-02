# Copyright 2023 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from .core import _component_databases


def get_component_registry(dbname):
    return _component_databases.get(dbname)


def is_component_registry_ready(dbname):
    """Return True if the registry is ready to be used."""
    comp_registry = get_component_registry(dbname)
    return comp_registry.ready if comp_registry else False
