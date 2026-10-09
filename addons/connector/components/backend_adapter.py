# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""

Backend Adapter
===============

An external adapter has a common interface to speak with the backend.
It translates the basic orders (search, read, write) to the protocol
used by the backend.

"""

from odoo.addons.component.core import AbstractComponent


class BackendAdapter(AbstractComponent):
    """Base Backend Adapter for the connectors"""

    _name = "base.backend.adapter"
    _inherit = "base.connector"
    _usage = "backend.adapter"


# pylint: disable=W8106
class CRUDAdapter(AbstractComponent):
    """Base External Adapter specialized in the handling
    of records on external systems.

    This is an empty shell, Components can inherit and implement their own
    implementation for the methods.

    """

    _name = "base.backend.adapter.crud"
    _inherit = "base.backend.adapter"
    _usage = "backend.adapter"

    def search(self, *args, **kwargs):
        """Search records according to some criterias
        and returns a list of ids"""
        raise NotImplementedError

    def read(self, *args, **kwargs):
        """Returns the information of a record"""
        raise NotImplementedError

    def search_read(self, *args, **kwargs):
        """Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, *args, **kwargs):
        """Create a record on the external system"""
        raise NotImplementedError

    def write(self, *args, **kwargs):
        """Update records on the external system"""
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        """Delete a record on the external system"""
        raise NotImplementedError
