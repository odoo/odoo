# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence
# This assume an existing database.
import psycopg2
import unittest2

import openerp
from openerp import SUPERUSER_ID
import common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

def registry(model):
    return openerp.modules.registry.RegistryManager.get(DB)[model]

def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

def get_module(module_name):
    registry = openerp.modules.registry.RegistryManager.get(DB)
    return registry.get(module_name)

def reload_registry():
    openerp.modules.registry.RegistryManager.new(
        DB, update_module=True)

def search_registry(model_name, domain):
    cr = cursor()
    model = registry(model_name)
    record_ids = model.search(cr, SUPERUSER_ID, domain, {})
    cr.close()
    return record_ids

def install_module(module_name):
    ir_module_module = registry('ir.module.module')
    cr = cursor()
    module_ids = ir_module_module.search(cr, SUPERUSER_ID,
        [('name', '=', module_name)], {})
    assert len(module_ids) == 1
    ir_module_module.button_install(cr, SUPERUSER_ID, module_ids, {})
    cr.commit()
    cr.close()
    reload_registry()

def uninstall_module(module_name):
    ir_module_module = registry('ir.module.module')
    cr = cursor()
    module_ids = ir_module_module.search(cr, SUPERUSER_ID,
        [('name', '=', module_name)], {})
    assert len(module_ids) == 1
    ir_module_module.button_uninstall(cr, SUPERUSER_ID, module_ids, {})
    cr.commit()
    cr.close()
    reload_registry()

class test_uninstall(unittest2.TestCase):
    """
    Test the install/uninstall of a test module. The module is available in
    `openerp.tests` which should be present in the addons-path.
    """

    def test_01_install(self):
        """ Check a few things showing the module is installed. """
        install_module('test_uninstall')
        assert get_module('test_uninstall.model')

        assert search_registry('ir.model.data',
            [('module', '=', 'test_uninstall')])

        assert search_registry('ir.model.fields',
            [('model', '=', 'test_uninstall.model')])

    def test_02_install(self):
        """ Check a few things showing the module is uninstalled. """
        uninstall_module('test_uninstall')
        assert not get_module('test_uninstall.model')

        assert not search_registry('ir.model.data',
            [('module', '=', 'test_uninstall')])

        assert not search_registry('ir.model.fields',
            [('model', '=', 'test_uninstall.model')])



if __name__ == '__main__':
    unittest2.main()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
