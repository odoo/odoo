# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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

import base64
import imp
import itertools
import logging
import os
import re
import sys
import zipfile
import zipimport

from cStringIO import StringIO
from os.path import join as opj
from zipfile import PyZipFile, ZIP_DEFLATED


import openerp
import openerp.modules.db
import openerp.modules.graph
import openerp.modules.migration
import openerp.netsvc as netsvc
import openerp.osv as osv
import openerp.pooler as pooler
import openerp.release as release
import openerp.tools as tools
import openerp.tools.osutil as osutil

from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.modules.module import \
    get_modules, get_modules_with_version, \
    load_information_from_description_file, \
    get_module_resource, zip_directory, \
    get_module_path, initialize_sys_path, \
    register_module_classes, init_module_models

logger = netsvc.Logger()


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
    logger = logging.getLogger('init.load')
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
        if not tools.config.options['test_disable']:
            try:
                _load_data(cr, module_name, idref, mode, 'test')
            except Exception, e:
                logging.getLogger('init.test').exception(
                    'Tests failed to execute in module %s', module_name)
            finally:
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
            logger.info("module %s: loading %s", module_name, filename)
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
                    tools.convert_yaml_import(cr, module_name, fp, idref, mode, noupdate)
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
    logger.debug('loading %d packages...', len(graph))

    # get db timestamp
    cr.execute("select now()::timestamp")
    dt_before_load = cr.fetchone()[0]

    # register, instantiate and initialize models for each modules
    for index, package in enumerate(graph):
        module_name = package.name
        module_id = package.id

        if skip_modules and module_name in skip_modules:
            continue

        logger.info('module %s: loading objects', package.name)
        migrations.migrate_module(package, 'pre')
        register_module_classes(package.name)
        models = pool.load(cr, package)
        loaded_modules.append(package.name)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_models(cr, package.name, models)

        status['progress'] = float(index) / len(graph)

        # Can't put this line out of the loop: ir.module.module will be
        # registered by init_module_models() above.
        modobj = pool.get('ir.module.module')

        if perform_checks:
            modobj.check(cr, 1, [module_id])

        idref = {}

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            if package.state=='to upgrade':
                # upgrading the module information
                modobj.write(cr, 1, [module_id], modobj.get_values_from_terp(package.data))
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
                load_test(module_name, idref, mode)

            processed_modules.append(package.name)

            migrations.migrate_module(package, 'post')

            ver = release.major_version + '.' + package.data['version']
            # Set new modules and dependencies
            modobj.write(cr, 1, [module_id], {'state': 'installed', 'latest_version': ver})
            # Update translations for all installed languages
            modobj.update_translations(cr, 1, [module_id], None)

            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)

        cr.commit()

    # mark new res_log records as read
    cr.execute("update res_log set read=True where create_date >= %s", (dt_before_load,))

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
            logging.getLogger('init').warning('invalid module names, ignored: %s', ", ".join(incorrect_names))

def load_marked_modules(cr, graph, states, force, progressdict, report, loaded_modules):
    """Loads modules marked with ``states``, adding them to ``graph`` and
       ``loaded_modules`` and returns a list of installed/upgraded modules."""
    processed_modules = []
    while True:
        cr.execute("SELECT name from ir_module_module WHERE state IN %s" ,(tuple(states),))
        module_list = [name for (name,) in cr.fetchall() if name not in graph]
        new_modules_in_graph = graph.add_modules(cr, module_list, force)
        logger.notifyChannel('init', netsvc.LOG_DEBUG, 'Updating graph with %d more modules' % (len(module_list)))
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
            logger.notifyChannel("init", netsvc.LOG_INFO, "init db")
            openerp.modules.db.initialize(cr)
            tools.config["init"]["all"] = 1
            tools.config['update']['all'] = 1
            if not tools.config['without_demo']:
                tools.config["demo"]['all'] = 1

        # This is a brand new pool, just created in pooler.get_db_and_pool()
        pool = pooler.get_pool(cr.dbname)

        report = tools.assertion_report()
        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

        # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps) 
        graph = openerp.modules.graph.Graph()
        graph.add_module(cr, 'base', force)
        if not graph:
            logger.notifyChannel('init', netsvc.LOG_CRITICAL, 'module base cannot be loaded! (hint: verify addons-path)')
            raise osv.osv.except_osv(_('Could not load base module'), _('module base cannot be loaded! (hint: verify addons-path)'))

        # processed_modules: for cleanup step after install
        # loaded_modules: to avoid double loading
        loaded_modules, processed_modules = load_module_graph(cr, graph, status, perform_checks=(not update_module), report=report)

        if tools.config['load_language']:
            for lang in tools.config['load_language'].split(','):
                tools.load_language(cr, lang)

        # STEP 2: Mark other modules to be loaded/updated
        if update_module:
            modobj = pool.get('ir.module.module')
            if ('base' in tools.config['init']) or ('base' in tools.config['update']):
                logger.notifyChannel('init', netsvc.LOG_INFO, 'updating modules list')
                modobj.update_list(cr, 1)

            _check_module_names(cr, itertools.chain(tools.config['init'].keys(), tools.config['update'].keys()))

            mods = [k for k in tools.config['init'] if tools.config['init'][k]]
            if mods:
                ids = modobj.search(cr, 1, ['&', ('state', '=', 'uninstalled'), ('name', 'in', mods)])
                if ids:
                    modobj.button_install(cr, 1, ids)

            mods = [k for k in tools.config['update'] if tools.config['update'][k]]
            if mods:
                ids = modobj.search(cr, 1, ['&', ('state', '=', 'installed'), ('name', 'in', mods)])
                if ids:
                    modobj.button_upgrade(cr, 1, ids)

            cr.execute("update ir_module_module set state=%s where name=%s", ('installed', 'base'))


        # STEP 3: Load marked modules (skipping base which was done in STEP 1)
        # IMPORTANT: this is done in two parts, first loading all installed or
        #            partially installed modules (i.e. installed/to upgrade), to
        #            offer a consistent system to the second part: installing
        #            newly selected modules.
        states_to_load = ['installed', 'to upgrade']
        processed = load_marked_modules(cr, graph, states_to_load, force, status, report, loaded_modules)
        processed_modules.extend(processed)
        if update_module:
            states_to_load = ['to install']
            processed = load_marked_modules(cr, graph, states_to_load, force, status, report, loaded_modules)
            processed_modules.extend(processed)

        # load custom models
        cr.execute('select model from ir_model where state=%s', ('manual',))
        for model in cr.dictfetchall():
            pool.get('ir.model').instanciate(cr, 1, model['model'], {})

        # STEP 4: Finish and cleanup
        if processed_modules:
            cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if model_obj and not model_obj.is_transient():
                    logger.notifyChannel('init', netsvc.LOG_WARNING, 'Model %s (%s) has no access rules!' % (model, name))

            # Temporary warning while we remove access rights on osv_memory objects, as they have
            # been replaced by owner-only access rights
            cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if model_obj and model_obj.is_transient():
                    logger.notifyChannel('init', netsvc.LOG_WARNING, 'The transient model %s (%s) should not have explicit access rules!' % (model, name))

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                obj = pool.get(model)
                if obj:
                    obj._check_removed_columns(cr, log=True)
                else:
                    logger.notifyChannel('init', netsvc.LOG_WARNING, "Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)" % model)

            # Cleanup orphan records
            pool.get('ir.model.data')._process_end(cr, 1, processed_modules)

        if report.get_report():
            logger.notifyChannel('init', netsvc.LOG_INFO, report)

        for kind in ('init', 'demo', 'update'):
            tools.config[kind] = {}

        cr.commit()
        if update_module:
            # Remove records referenced from ir_model_data for modules to be
            # removed (and removed the references from ir_model_data).
            cr.execute("select id,name from ir_module_module where state=%s", ('to remove',))
            for mod_id, mod_name in cr.fetchall():
                cr.execute('select model,res_id from ir_model_data where noupdate=%s and module=%s order by id desc', (False, mod_name,))
                for rmod, rid in cr.fetchall():
                    uid = 1
                    rmod_module= pool.get(rmod)
                    if rmod_module:
                        # TODO group by module so that we can delete multiple ids in a call
                        rmod_module.unlink(cr, uid, [rid])
                    else:
                        logger.notifyChannel('init', netsvc.LOG_ERROR, 'Could not locate %s to remove res=%d' % (rmod,rid))
                cr.execute('delete from ir_model_data where noupdate=%s and module=%s', (False, mod_name,))
                cr.commit()

            # Remove menu items that are not referenced by any of other
            # (child) menu item, ir_values, or ir_model_data.
            # This code could be a method of ir_ui_menu.
            # TODO: remove menu without actions of children
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
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'removed %d unused menus' % (cr.rowcount,))

            # Pretend that modules to be removed are actually uninstalled.
            cr.execute("update ir_module_module set state=%s where state=%s", ('uninstalled', 'to remove',))
            cr.commit()
    finally:
        cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
