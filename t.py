import openerp
from openerp.osv import fields
from openerp.osv.orm import Model
conf = openerp.tools.config

if __name__ == '__main__':
    openerp.netsvc.init_logger()
    conf['addons_path'] = './openerp/tests/addons'
    conf['init'] = {'test_uninstall': 1}
    registry = openerp.modules.registry.RegistryManager.new('xx', update_module=True)
    ir_model_constraint = registry.get('ir.model.constraint')
    print ir_model_constraint
    cr = registry.db.cursor()
    ids = ir_model_constraint.search(cr, openerp.SUPERUSER_ID, [], {})
    print ir_model_constraint.browse(cr, openerp.SUPERUSER_ID, ids, {})
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

def create_virtual_module(db_name, module_name, info):
    registry = openerp.modules.registry.RegistryManager.get(db_name)
    cr = registry.db.cursor()

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
