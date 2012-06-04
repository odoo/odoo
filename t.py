import sys

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields
from openerp.osv.orm import Model
conf = openerp.tools.config

# TODO Exception handling (especially on cursors).

DB = None

def registry(model_name):
    return openerp.modules.registry.RegistryManager.get(DB)[model_name]

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

if __name__ == '__main__':
    assert len(sys.argv) == 2
    DB = sys.argv[1]
    openerp.netsvc.init_logger()
    conf['addons_path'] = './openerp/tests/addons,../../addons/trunk,../../web/trunk/addons'

    install_module('test_uninstall')
    assert get_module('test_uninstall.model')

    assert search_registry('ir.model.data',
        [('module', '=', 'test_uninstall')])

    assert search_registry('ir.model.fields',
        [('model', '=', 'test_uninstall.model')])

    uninstall_module('test_uninstall')
    assert not get_module('test_uninstall.model')

    assert not search_registry('ir.model.data',
        [('module', '=', 'test_uninstall')])

    assert not search_registry('ir.model.fields',
        [('model', '=', 'test_uninstall.model')])

    ir_model_constraint = registry('ir.model.constraint')
    cr = cursor()
    ids = ir_model_constraint.search(cr, SUPERUSER_ID, [], {})
    #print ir_model_constraint.browse(cr, SUPERUSER_ID, ids, {})
    cr.close()

#####################################################################

# Nice idea, but won't work without some more change to the framework (which
# expects everything on disk, maybe we can craft a zip file...).

MY_MODULE = {
    'author': 'Jean Beauvoir',
    'website': 'http://www.youtube.com/watch?v=FeO5DfdZi7Y',
    'name': 'FEEL THE HEAT',
    'description': "Cobra's theme",
    'web': False,
    'license': 'WTFPL',
    'application': False,
    'icon': False,
    'sequence': 100,
    'depends': ['base'],
}

def create_virtual_module(module_name, info):
    cr = cursor()

    cr.execute("""SELECT 1 FROM ir_module_module WHERE name=%s""", (module_name,))
    if cr.fetchone(): return

    category_id = openerp.modules.db.create_categories(cr, ['Tests'])
    cr.execute('INSERT INTO ir_module_module \
            (author, website, name, shortdesc, description, \
                category_id, auto_install, state, certificate, web, license, application, icon, sequence) \
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id', (
        info['author'],
        info['website'], module_name, info['name'],
        info['description'], category_id,
        True, 'to install', False,
        info['web'],
        info['license'],
        info['application'], info['icon'],
        info['sequence']))
    module_id = cr.fetchone()[0]
    cr.execute('INSERT INTO ir_model_data \
        (name,model,module, res_id, noupdate) VALUES (%s,%s,%s,%s,%s)', (
            'module_' + module_name, 'ir.module.module', 'base', module_id, True))
    dependencies = info['depends']
    for d in dependencies:
        cr.execute('INSERT INTO ir_module_module_dependency \
                (module_id,name) VALUES (%s, %s)', (module_id, d))

    cr.commit()
    cr.close()
