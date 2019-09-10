# -*- coding: utf-8 -*-
# This assumes an existing but uninitialized database.
import unittest2

import openerp
from openerp import SUPERUSER_ID
import common

ADMIN_USER_ID = common.ADMIN_USER_ID

def registry(model):
    return openerp.modules.registry.RegistryManager.get(common.get_db_name())[model]

def cursor():
    return openerp.modules.registry.RegistryManager.get(common.get_db_name()).cursor()

def get_module(module_name):
    registry = openerp.modules.registry.RegistryManager.get(common.get_db_name())
    return registry.get(module_name)

def reload_registry():
    openerp.modules.registry.RegistryManager.new(
        common.get_db_name(), update_module=True)

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

    def test_02_uninstall(self):
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
