# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

import openerp
import openerp.modules.db
import openerp.modules.graph
import openerp.modules.migration
import openerp.osv as osv
import openerp.pooler as pooler
import openerp.release as release
import openerp.tools as tools
import openerp.tools.assertion_report as assertion_report
from openerp import SUPERUSER_ID

from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.modules.module import initialize_sys_path, \
    load_openerp_module, init_module_models

_logger = logging.getLogger(__name__)

def open_openerp_namespace():
    # See comment for open_openerp_namespace.
    if openerp.conf.deprecation.open_openerp_namespace:
        for k, v in list(sys.modules.items()):
            if k.startswith('openerp.') and sys.modules.get(k[8:]) is None:
                sys.modules[k[8:]] = v


def load_module_graph(cr, graph, status=None, perform_checks=True, skip_modules=None, report=None):
    """Migrates+Updates or Installs all module nodes from ``graph``
       :param graph: graph of module nodes to load
       :param status: status dictionary for keeping track of progress
       :param perform_checks: whether module descriptors should be checked for validity (prints warnings
                              for same cases, and even raise osv_except if certificate is invalid)
       :param skip_modules: optional list of module names (packages) which have previously been loaded and can be skipped
       :return: list of modules that were installed or updated
    """
    def process_sql_file(cr, fp):
        queries = fp.read().split(';')
        for query in queries:
            new_query = ' '.join(query.split())
            if new_query:
                cr.execute(new_query)

    load_init_xml = lambda *args: _load_data(cr, *args, kind='init_xml')
    load_update_xml = lambda *args: _load_data(cr, *args, kind='update_xml')
    load_demo_xml = lambda *args: _load_data(cr, *args, kind='demo_xml')
    load_data = lambda *args: _load_data(cr, *args, kind='data')
    load_demo = lambda *args: _load_data(cr, *args, kind='demo')

    def load_test(module_name, idref, mode):
        cr.commit()
        try:
            threading.currentThread().testing = True
            _load_data(cr, module_name, idref, mode, 'test')
            return True
        except Exception:
            _logger.exception(
                'module %s: an exception occurred in a test', module_name)
            return False
        finally:
            threading.currentThread().testing = False
            if tools.config.options['test_commit']:
                cr.commit()
            else:
                cr.rollback()

    def _load_data(cr, module_name, idref, mode, kind):
        """

        kind: data, demo, test, init_xml, update_xml, demo_xml.

        noupdate is False, unless it is demo data or it is csv data in
        init mode.

        """
        for filename in package.data[kind]:
            _logger.info("module %s: loading %s", module_name, filename)
            _, ext = os.path.splitext(filename)
            pathname = os.path.join(module_name, filename)
            fp = tools.file_open(pathname)
            noupdate = False
            if kind in ('demo', 'demo_xml'):
                noupdate = True
            try:
                if ext == '.csv':
                    if kind in ('init', 'init_xml'):
                        noupdate = True
                    tools.convert_csv_import(cr, module_name, pathname, fp.read(), idref, mode, noupdate)
                elif ext == '.sql':
                    process_sql_file(cr, fp)
                elif ext == '.yml':
                    tools.convert_yaml_import(cr, module_name, fp, kind, idref, mode, noupdate, report)
                else:
                    tools.convert_xml_import(cr, module_name, fp, idref, mode, noupdate, report)
            finally:
                fp.close()

    if status is None:
        status = {}

    processed_modules = []
    loaded_modules = []
    pool = pooler.get_pool(cr.dbname)
    migrations = openerp.modules.migration.MigrationManager(cr, graph)
    _logger.debug('loading %d packages...', len(graph))

    # get db timestamp
    cr.execute("select (now() at time zone 'UTC')::timestamp")
    dt_before_load = cr.fetchone()[0]

    # register, instantiate and initialize models for each modules
    for index, package in enumerate(graph):
        module_name = package.name
        module_id = package.id

        if skip_modules and module_name in skip_modules:
            continue

        _logger.info('module %s: loading objects', package.name)
        migrations.migrate_module(package, 'pre')
        load_openerp_module(package.name)

        models = pool.load(cr, package)
        loaded_modules.append(package.name)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_models(cr, package.name, models)
        pool._init_modules.add(package.name)
        status['progress'] = float(index) / len(graph)

        # Can't put this line out of the loop: ir.module.module will be
        # registered by init_module_models() above.
        modobj = pool.get('ir.module.module')

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
            load_init_xml(module_name, idref, mode)
            load_update_xml(module_name, idref, mode)
            load_data(module_name, idref, mode)
            if hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed'):
                status['progress'] = (index + 0.75) / len(graph)
                load_demo_xml(module_name, idref, mode)
                load_demo(module_name, idref, mode)
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, module_id))

                # launch tests only in demo mode, as most tests will depend
                # on demo data. Other tests can be added into the regular
                # 'data' section, but should probably not alter the data,
                # as there is no rollback.
                if tools.config.options['test_enable']:
                    report.record_result(load_test(module_name, idref, mode))

                    # Run the `fast_suite` and `checks` tests given by the module.
                    if module_name == 'base':
                        # Also run the core tests after the database is created.
                        report.record_result(openerp.modules.module.run_unit_tests('openerp'))
                    report.record_result(openerp.modules.module.run_unit_tests(module_name))

            processed_modules.append(package.name)

            migrations.migrate_module(package, 'post')

            ver = release.major_version + '.' + package.data['version']
            # Set new modules and dependencies
            modobj.write(cr, SUPERUSER_ID, [module_id], {'state': 'installed', 'latest_version': ver})
            # Update translations for all installed languages
            modobj.update_translations(cr, SUPERUSER_ID, [module_id], None)

            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)

        cr.commit()
    
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

def load_marked_modules(cr, graph, states, force, progressdict, report, loaded_modules):
    """Loads modules marked with ``states``, adding them to ``graph`` and
       ``loaded_modules`` and returns a list of installed/upgraded modules."""
    processed_modules = []
    while True:
        cr.execute("SELECT name from ir_module_module WHERE state IN %s" ,(tuple(states),))
        module_list = [name for (name,) in cr.fetchall() if name not in graph]
        graph.add_modules(cr, module_list, force)
        _logger.debug('Updating graph with %d more modules', len(module_list))
        loaded, processed = load_module_graph(cr, graph, progressdict, report=report, skip_modules=loaded_modules)
        processed_modules.extend(processed)
        loaded_modules.extend(loaded)
        if not processed: break
    return processed_modules


def load_modules(db, force_demo=False, status=None, update_module=False):
    # TODO status['progress'] reporting is broken: used twice (and reset each
    # time to zero) in load_module_graph, not fine-grained enough.
    # It should be a method exposed by the pool.
    initialize_sys_path()

    open_openerp_namespace()

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

        # This is a brand new pool, just created in pooler.get_db_and_pool()
        pool = pooler.get_pool(cr.dbname)

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
        report = assertion_report.assertion_report()
        loaded_modules, processed_modules = load_module_graph(cr, graph, status, perform_checks=(not update_module), report=report)

        if tools.config['load_language']:
            for lang in tools.config['load_language'].split(','):
                tools.load_language(cr, lang)

        # STEP 2: Mark other modules to be loaded/updated
        if update_module:
            modobj = pool.get('ir.module.module')
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
        states_to_load = ['installed', 'to upgrade', 'to remove']
        processed = load_marked_modules(cr, graph, states_to_load, force, status, report, loaded_modules)
        processed_modules.extend(processed)
        if update_module:
            states_to_load = ['to install']
            processed = load_marked_modules(cr, graph, states_to_load, force, status, report, loaded_modules)
            processed_modules.extend(processed)

        # load custom models
        cr.execute('select model from ir_model where state=%s', ('manual',))
        for model in cr.dictfetchall():
            pool.get('ir.model').instanciate(cr, SUPERUSER_ID, model['model'], {})

        # STEP 4: Finish and cleanup installations
        if processed_modules:
            cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if model_obj and not model_obj.is_transient():
                    _logger.warning('Model %s (%s) has no access rules!', model, name)

            # Temporary warning while we remove access rights on osv_memory objects, as they have
            # been replaced by owner-only access rights
            cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if model_obj and model_obj.is_transient():
                    _logger.warning('The transient model %s (%s) should not have explicit access rules!', model, name)

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                obj = pool.get(model)
                if obj:
                    obj._check_removed_columns(cr, log=True)
                else:
                    _logger.warning("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

            # Cleanup orphan records
            pool.get('ir.model.data')._process_end(cr, SUPERUSER_ID, processed_modules)

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
            cr.execute("SELECT id FROM ir_module_module WHERE state=%s", ('to remove',))
            mod_ids_to_remove = [x[0] for x in cr.fetchall()]
            if mod_ids_to_remove:
                pool.get('ir.module.module').module_uninstall(cr, SUPERUSER_ID, mod_ids_to_remove)
                # Recursive reload, should only happen once, because there should be no
                # modules to remove next time
                cr.commit()
                _logger.info('Reloading registry once more after uninstalling modules')
                return pooler.restart_pool(cr.dbname, force_demo, status, update_module)

        if report.failures:
            _logger.error('At least one test failed when loading the modules.')
        else:
            _logger.info('Modules loaded.')
    finally:
        cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
