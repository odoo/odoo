# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from ..connector import ConnectorUnit


class BackendAdapter(ConnectorUnit):
    """ Base Backend Adapter for the connectors """

    _model_name = None  # define in sub-classes


class CRUDAdapter(BackendAdapter):
    """ Base External Adapter specialized in the handling
    of records on external systems.

    Subclasses can implement their own implementation for
    the methods.
    """

    _model_name = None

    def search(self, *args, **kwargs):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, *args, **kwargs):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, *args, **kwargs):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, *args, **kwargs):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, *args, **kwargs):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        """ Delete a record on the external system """
        raise NotImplementedError
