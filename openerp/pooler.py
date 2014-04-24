# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

""" Functions kept for backward compatibility.

    They are simple wrappers around a global RegistryManager methods.

"""

import logging
import openerp.conf.deprecation
from openerp.modules.registry import RegistryManager

_logger = logging.getLogger(__name__)

def get_db_and_pool(db_name, force_demo=False, status=None, update_module=False):
    """Create and return a database connection and a newly initialized registry."""
    assert openerp.conf.deprecation.openerp_pooler
    _logger.warning('openerp.pooler.get_db_and_pool() is deprecated.')
    registry = RegistryManager.get(db_name, force_demo, status, update_module)
    return registry._db, registry


def restart_pool(db_name, force_demo=False, status=None, update_module=False):
    """Delete an existing registry and return a database connection and a newly initialized registry."""
    _logger.warning('openerp.pooler.restart_pool() is deprecated.')
    assert openerp.conf.deprecation.openerp_pooler
    registry = RegistryManager.new(db_name, force_demo, status, update_module)
    return registry._db, registry

def get_db(db_name):
    """Return a database connection. The corresponding registry is initialized."""
    assert openerp.conf.deprecation.openerp_pooler
    return get_db_and_pool(db_name)[0]


def get_pool(db_name, force_demo=False, status=None, update_module=False):
    """Return a model registry."""
    assert openerp.conf.deprecation.openerp_pooler
    return get_db_and_pool(db_name, force_demo, status, update_module)[1]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
