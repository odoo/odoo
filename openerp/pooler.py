# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
