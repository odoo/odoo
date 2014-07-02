# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2014 OpenERP s.a. (<http://openerp.com>).
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

""" Modules (also called addons) management.

"""

import itertools
import logging
import os
import sys
import threading
import time

import openerp
import openerp.modules.db
import openerp.modules.graph
import openerp.modules.migration
import openerp.modules.registry
import openerp.osv as osv
import openerp.tools as tools
from openerp import SUPERUSER_ID

from openerp.tools.translate import _
from openerp.modules.module import initialize_sys_path, \
    load_openerp_module, init_module_models, adapt_version
from module import runs_post_install

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('openerp.tests')


def load_module_graph(cr, graph, status=None, perform_checks=True, skip_modules=None, report=None):
    """Migrates+Updates or Installs all module nodes from ``graph``
       :param graph: graph of module nodes to load
       :param status: status dictionary for keeping track of progress
       :param perform_checks: whether module descriptors should be checked for validity (prints warnings
                              for same cases)
       :param skip_modules: optional list of module names (packages) which have previously been loaded and can be skipped
       :return: list of modules that were installed or updated
    """
    def load_test(module_name, idref, mode):
        cr.commit()
        try:
            _load_data(cr, module_name, idref, mode, 'test')
            return True
        except Exception:
            _test_logger.exception(
                'module %s: an exception occurred in a test', module_name)
            return False
        finally:
            if tools.config.options['test_commit']:
                cr.commit()
            else:
                cr.rollback()
                # avoid keeping stale xml_id, etc. in cache 
                openerp.modules.registry.RegistryManager.clear_caches(cr.dbname)


    def _get_files_of_kind(kind):
        if kind == 'demo':
            kind = ['demo_xml', 'demo']
        elif kind == 'data':
            kind = ['init_xml', 'update_xml', 'data']
        if isinstance(kind, str):
            kind = [kind]
        files = []
        for k in kind:
            for f in package.data[k]:
                files.append(f)
                if k.endswith('_xml') and not (k == 'init_xml' and not f.endswith('.xml')):
                    # init_xml, update_xml and demo_xml are deprecated except
                    # for the case of init_xml with yaml, csv and sql files as
                    # we can't specify noupdate for those file.
                    correct_key = 'demo' if k.count('demo') else 'data'
                    _logger.warning(
                        "module %s: key '%s' is deprecated in favor of '%s' for file '%s'.",
                        package.name, k, correct_key, f
                    )
        return files

    def _load_data(cr, module_name, idref, mode, kind):
        """

        kind: data, demo, test, init_xml, update_xml, demo_xml.

        noupdate is False, unless it is demo data or it is csv data in
        init mode.

        """
        try:
            if kind in ('demo', 'test'):
                threading.currentThread().testing = True
            for filename in _get_files_of_kind(kind):
                _logger.info("loading %s/%s", module_name, filename)
                noupdate = False
                if kind in ('demo', 'demo_xml') or (filename.endswith('.csv') and kind in ('init', 'init_xml')):
                    noupdate = True
                tools.convert_file(cr, module_name, filename, idref, mode, noupdate, kind, report)
        finally:
            if kind in ('demo', 'test'):
                threading.currentThread().testing = False

    if status is None:
        status = {}

    processed_modules = []
    loaded_modules = []
    registry = openerp.registry(cr.dbname)
    migrations = openerp.modules.migration.MigrationManager(cr, graph)
    _logger.info('loading %d modules...', len(graph))

    # Query manual fields for all models at once and save them on the registry
    # so the initialization code for each model does not have to do it
    # one model at a time.
    registry.fields_by_model = {}
    cr.execute('SELECT * FROM ir_model_fields WHERE state=%s', ('manual',))
    for field in cr.dictfetchall():
        registry.fields_by_model.setdefault(field['model'], []).append(field)

    # register, instantiate and initialize models for each modules
    t0 = time.time()
    t0_sql = openerp.sql_db.sql_counter

    for index, package in enumerate(graph):
        module_name = package.name
        module_id = package.id

        if skip_modules and module_name in skip_modules:
            continue

        migrations.migrate_module(package, 'pre')
        load_openerp_module(package.name)

        new_install = package.installed_version is None
        if new_install:
            py_module = sys.modules['openerp.addons.%s' % (module_name,)]
            pre_init = package.info.get('pre_init_hook')
            if pre_init:
                getattr(py_module, pre_init)(cr)

        models = registry.load(cr, package)

        loaded_modules.append(package.name)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_models(cr, package.name, models)
        status['progress'] = float(index) / len(graph)

        # Can't put this line out of the loop: ir.module.module will be
        # registered by init_module_models() above.
        modobj = registry['ir.module.module']

        if perform_checks:
            modobj.check(cr, SUPERUSER_ID, [module_id])

        idref = {}

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            if package.state=='to upgrade':
                # upgrading the module information
                modobj.write(cr, SUPERUSER_ID, [module_id], modobj.get_values_from_terp(package.data))
            _load_data(cr, module_name, idref, mode, kind='data')
            has_demo = hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed')
            if has_demo:
                status['progress'] = (index + 0.75) / len(graph)
                _load_data(cr, module_name, idref, mode, kind='demo')
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, module_id))

            migrations.migrate_module(package, 'post')

            if new_install:
                post_init = package.info.get('post_init_hook')
                if post_init:
                    getattr(py_module, post_init)(cr, registry)

            registry._init_modules.add(package.name)
            # validate all the views at a whole
            registry['ir.ui.view']._validate_module_views(cr, SUPERUSER_ID, module_name)

            if has_demo:
                # launch tests only in demo mode, allowing tests to use demo data.
                if tools.config.options['test_enable']:
                    # Yamel test
                    report.record_result(load_test(module_name, idref, mode))
                    # Python tests
                    ir_http = registry['ir.http']
                    if hasattr(ir_http, '_routing_map'):
                        # Force routing map to be rebuilt between each module test suite
                        del(ir_http._routing_map)
                    report.record_result(openerp.modules.module.run_unit_tests(module_name, cr.dbname))

            processed_modules.append(package.name)

            ver = adapt_version(package.data['version'])
            # Set new modules and dependencies
            modobj.write(cr, SUPERUSER_ID, [module_id], {'state': 'installed', 'latest_version': ver})
            # Update translations for all installed languages
            modobj.update_translations(cr, SUPERUSER_ID, [module_id], None, {'overwrite': openerp.tools.config["overwrite_existing_translations"]})

            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)

        registry._init_modules.add(package.name)
        cr.commit()

    _logger.log(25, "%s modules loaded in %.2fs, %s queries", len(graph), time.time() - t0, openerp.sql_db.sql_counter - t0_sql)

    # The query won't be valid for models created later (i.e. custom model
    # created after the registry has been loaded), so empty its result.
    registry.fields_by_model = None

    cr.commit()

    return loaded_modules, processed_modules

def _check_module_names(cr, module_names):
    mod_names = set(module_names)
    if 'base' in mod_names:
        # ignore dummy 'all' module
        if 'all' in mod_names:
            mod_names.remove('all')
    if mod_names:
        cr.execute("SELECT count(id) AS count FROM ir_module_module WHERE name in %s", (tuple(mod_names),))
        if cr.dictfetchone()['count'] != len(mod_names):
            # find out what module name(s) are incorrect:
            cr.execute("SELECT name FROM ir_module_module")
            incorrect_names = mod_names.difference([x['name'] for x in cr.dictfetchall()])
            _logger.warning('invalid module names, ignored: %s', ", ".join(incorrect_names))

def load_marked_modules(cr, graph, states, force, progressdict, report, loaded_modules, perform_checks):
    """Loads modules marked with ``states``, adding them to ``graph`` and
       ``loaded_modules`` and returns a list of installed/upgraded modules."""
    processed_modules = []
    while True:
        cr.execute("SELECT name from ir_module_module WHERE state IN %s" ,(tuple(states),))
        module_list = [name for (name,) in cr.fetchall() if name not in graph]
        graph.add_modules(cr, module_list, force)
        _logger.debug('Updating graph with %d more modules', len(module_list))
        loaded, processed = load_module_graph(cr, graph, progressdict, report=report, skip_modules=loaded_modules, perform_checks=perform_checks)
        processed_modules.extend(processed)
        loaded_modules.extend(loaded)
        if not processed: break
    return processed_modules

def load_modules(db, force_demo=False, status=None, update_module=False):
    # TODO status['progress'] reporting is broken: used twice (and reset each
    # time to zero) in load_module_graph, not fine-grained enough.
    # It should be a method exposed by the registry.
    initialize_sys_path()

    force = []
    if force_demo:
        force.append('demo')

    cr = db.cursor()
    try:
        if not openerp.modules.db.is_initialized(cr):
            _logger.info("init db")
            openerp.modules.db.initialize(cr)
            tools.config["init"]["all"] = 1
            tools.config['update']['all'] = 1
            if not tools.config['without_demo']:
                tools.config["demo"]['all'] = 1

        # This is a brand new registry, just created in
        # openerp.modules.registry.RegistryManager.new().
        registry = openerp.registry(cr.dbname)

        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

        # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps) 
        graph = openerp.modules.graph.Graph()
        graph.add_module(cr, 'base', force)
        if not graph:
            _logger.critical('module base cannot be loaded! (hint: verify addons-path)')
            raise osv.osv.except_osv(_('Could not load base module'), _('module base cannot be loaded! (hint: verify addons-path)'))

        # processed_modules: for cleanup step after install
        # loaded_modules: to avoid double loading
        report = registry._assertion_report
        loaded_modules, processed_modules = load_module_graph(cr, graph, status, perform_checks=update_module, report=report)

        if tools.config['load_language']:
            for lang in tools.config['load_language'].split(','):
                tools.load_language(cr, lang)

        # STEP 2: Mark other modules to be loaded/updated
        if update_module:
            modobj = registry['ir.module.module']
            if ('base' in tools.config['init']) or ('base' in tools.config['update']):
                _logger.info('updating modules list')
                modobj.update_list(cr, SUPERUSER_ID)

            _check_module_names(cr, itertools.chain(tools.config['init'].keys(), tools.config['update'].keys()))

            mods = [k for k in tools.config['init'] if tools.config['init'][k]]
            if mods:
                ids = modobj.search(cr, SUPERUSER_ID, ['&', ('state', '=', 'uninstalled'), ('name', 'in', mods)])
                if ids:
                    modobj.button_install(cr, SUPERUSER_ID, ids)

            mods = [k for k in tools.config['update'] if tools.config['update'][k]]
            if mods:
                ids = modobj.search(cr, SUPERUSER_ID, ['&', ('state', '=', 'installed'), ('name', 'in', mods)])
                if ids:
                    modobj.button_upgrade(cr, SUPERUSER_ID, ids)

            cr.execute("update ir_module_module set state=%s where name=%s", ('installed', 'base'))


        # STEP 3: Load marked modules (skipping base which was done in STEP 1)
        # IMPORTANT: this is done in two parts, first loading all installed or
        #            partially installed modules (i.e. installed/to upgrade), to
        #            offer a consistent system to the second part: installing
        #            newly selected modules.
        #            We include the modules 'to remove' in the first step, because
        #            they are part of the "currently installed" modules. They will
        #            be dropped in STEP 6 later, before restarting the loading
        #            process.
        # IMPORTANT 2: We have to loop here until all relevant modules have been
        #              processed, because in some rare cases the dependencies have
        #              changed, and modules that depend on an uninstalled module
        #              will not be processed on the first pass.
        #              It's especially useful for migrations.
        previously_processed = -1
        while previously_processed < len(processed_modules):
            previously_processed = len(processed_modules)
            processed_modules += load_marked_modules(cr, graph,
                ['installed', 'to upgrade', 'to remove'],
                force, status, report, loaded_modules, update_module)
            if update_module:
                processed_modules += load_marked_modules(cr, graph,
                    ['to install'], force, status, report,
                    loaded_modules, update_module)

        # load custom models
        cr.execute('select model from ir_model where state=%s', ('manual',))
        for model in cr.dictfetchall():
            registry['ir.model'].instanciate(cr, SUPERUSER_ID, model['model'], {})

        # STEP 4: Finish and cleanup installations
        if processed_modules:
            cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                if model in registry and not registry[model].is_transient() and not isinstance(registry[model], openerp.osv.orm.AbstractModel):
                    _logger.warning('The model %s has no access rules, consider adding one. E.g. access_%s,access_%s,model_%s,,1,1,1,1',
                        model, model.replace('.', '_'), model.replace('.', '_'), model.replace('.', '_'))

            # Temporary warning while we remove access rights on osv_memory objects, as they have
            # been replaced by owner-only access rights
            cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
            for (model, name) in cr.fetchall():
                if model in registry and registry[model].is_transient():
                    _logger.warning('The transient model %s (%s) should not have explicit access rules!', model, name)

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                if model in registry:
                    registry[model]._check_removed_columns(cr, log=True)
                else:
                    _logger.warning("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

            # Cleanup orphan records
            registry['ir.model.data']._process_end(cr, SUPERUSER_ID, processed_modules)

        for kind in ('init', 'demo', 'update'):
            tools.config[kind] = {}

        cr.commit()

        # STEP 5: Cleanup menus 
        # Remove menu items that are not referenced by any of other
        # (child) menu item, ir_values, or ir_model_data.
        # TODO: This code could be a method of ir_ui_menu. Remove menu without actions of children
        if update_module:
            while True:
                cr.execute('''delete from
                        ir_ui_menu
                    where
                        (id not IN (select parent_id from ir_ui_menu where parent_id is not null))
                    and
                        (id not IN (select res_id from ir_values where model='ir.ui.menu'))
                    and
                        (id not IN (select res_id from ir_model_data where model='ir.ui.menu'))''')
                cr.commit()
                if not cr.rowcount:
                    break
                else:
                    _logger.info('removed %d unused menus', cr.rowcount)

        # STEP 6: Uninstall modules to remove
        if update_module:
            # Remove records referenced from ir_model_data for modules to be
            # removed (and removed the references from ir_model_data).
            cr.execute("SELECT name, id FROM ir_module_module WHERE state=%s", ('to remove',))
            modules_to_remove = dict(cr.fetchall())
            if modules_to_remove:
                pkgs = reversed([p for p in graph if p.name in modules_to_remove])
                for pkg in pkgs:
                    uninstall_hook = pkg.info.get('uninstall_hook')
                    if uninstall_hook:
                        py_module = sys.modules['openerp.addons.%s' % (pkg.name,)]
                        getattr(py_module, uninstall_hook)(cr, registry)

                registry['ir.module.module'].module_uninstall(cr, SUPERUSER_ID, modules_to_remove.values())
                # Recursive reload, should only happen once, because there should be no
                # modules to remove next time
                cr.commit()
                _logger.info('Reloading registry once more after uninstalling modules')
                return openerp.modules.registry.RegistryManager.new(cr.dbname, force_demo, status, update_module)

        # STEP 7: verify custom views on every model
        if update_module:
            Views = registry['ir.ui.view']
            custom_view_test = True
            for model in registry.models.keys():
                if not Views._validate_custom_views(cr, SUPERUSER_ID, model):
                    custom_view_test = False
                    _logger.error('invalid custom view(s) for model %s', model)
            report.record_result(custom_view_test)

        if report.failures:
            _logger.error('At least one test failed when loading the modules.')
        else:
            _logger.info('Modules loaded.')

        # STEP 8: call _register_hook on every model
        for model in registry.models.values():
            model._register_hook(cr)

        # STEP 9: Run the post-install tests
        cr.commit()

        t0 = time.time()
        t0_sql = openerp.sql_db.sql_counter
        if openerp.tools.config['test_enable']:
            cr.execute("SELECT name FROM ir_module_module WHERE state='installed'")
            for module_name in cr.fetchall():
                report.record_result(openerp.modules.module.run_unit_tests(module_name[0], cr.dbname, position=runs_post_install))
            _logger.log(25, "All post-tested in %.2fs, %s queries", time.time() - t0, openerp.sql_db.sql_counter - t0_sql)
    finally:
        cr.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
