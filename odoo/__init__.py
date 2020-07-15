# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#----------------------------------------------------------
# odoo must be a namespace package for odoo.addons to become one too
# https://packaging.python.org/guides/packaging-namespace-packages/
#----------------------------------------------------------    
__path__ = [
    __import__("os").path.abspath(path)
    for path in __import__("pkgutil").extend_path(__path__, __name__)
]


#----------------------------------------------------------
# Effective booting
# librares configuration, cli/config loading, environment setup
#----------------------------------------------------------
__import__("importlib").import_module("odoo.bootstrap").boot()


#----------------------------------------------------------
# Aliases
#----------------------------------------------------------
from odoo.tools.translate import _, _lt
from odoo.config import config

# The hard-coded super-user id (a.k.a. administrator, or root user).
SUPERUSER_ID = 1

def registry(database_name=None):
    """
    Return the model registry for the given database, or the database mentioned
    on the current thread. If the registry does not exist yet, it is created on
    the fly.
    """
    if database_name is None:
        import threading
        database_name = threading.currentThread().dbname
    return modules.registry.Registry(database_name)
