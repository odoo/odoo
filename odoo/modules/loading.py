# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules (also called addons) management.

"""

import itertools
import logging
import sys
import threading
import time

import odoo
import odoo.modules.db
import odoo.modules.graph
import odoo.modules.migration
import odoo.modules.registry
import odoo.tools as tools

from odoo import api, SUPERUSER_ID
from odoo.modules.module import adapt_version, initialize_sys_path, \
                                load_openerp_module, runs_post_install

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')


def load_module_graph(cr, graph, status=None, perform_checks=True, skip_modules=None, report=None):
    """Migrates+Updates or Installs all module nodes from ``graph``
       :param graph: graph of module nodes to load
       :param status: deprecated parameter, unused, left to avoid changing signature in 8.0
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
                odoo.registry(cr.dbname).clear_caches()


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

    processed_modules = []
    loaded_modules = []
    registry = odoo.registry(cr.dbname)
    migrations = odoo.modules.migration.MigrationManager(cr, graph)
    module_count = len(graph)
    _logger.info('loading %d modules...', module_count)

    registry.clear_manual_fields()

    # register, instantiate and initialize models for each modules
    t0 = time.time()
    t0_sql = odoo.sql_db.sql_counter

    for index, package in enumerate(graph, 1):
        module_name = package.name
        module_id = package.id

        if skip_modules and module_name in skip_modules:
            continue

        _logger.debug('loading module %s (%d/%d)', module_name, index, module_count)
        migrations.migrate_module(package, 'pre')
        load_openerp_module(package.name)

        new_install = package.state == 'to install'
        if new_install:
            py_module = sys.modules['odoo.addons.%s' % (module_name,)]
            pre_init = package.info.get('pre_init_hook')
            if pre_init:
                getattr(py_module, pre_init)(cr)

        model_names = registry.load(cr, package)

        loaded_modules.append(package.name)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            registry.setup_models(cr, partial=True)
            registry.init_models(cr, model_names, {'module': package.name})

        idref = {}

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            env = api.Environment(cr, SUPERUSER_ID, {})
            # Can't put this line out of the loop: ir.module.module will be
            # registered by init_models() above.
            module = env['ir.module.module'].browse(module_id)

            if perform_checks:
                module.check()

            if package.state=='to upgrade':
                # upgrading the module information
                module.write(module.get_values_from_terp(package.data))
            _load_data(cr, module_name, idref, mode, kind='data')
            has_demo = hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed')
            if has_demo:
                _load_data(cr, module_name, idref, mode, kind='demo')
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, module_id))
                module.invalidate_cache(['demo'])

            migrations.migrate_module(package, 'post')

            # Update translations for all installed languages
            overwrite = odoo.tools.config["overwrite_existing_translations"]
            module.with_context(overwrite=overwrite).update_translations()

            registry._init_modules.add(package.name)

            if new_install:
                post_init = package.info.get('post_init_hook')
                if post_init:
                    getattr(py_module, post_init)(cr, registry)

            # validate all the views at a whole
            env['ir.ui.view']._validate_module_views(module_name)

            if has_demo:
                # launch tests only in demo mode, allowing tests to use demo data.
                if tools.config.options['test_enable']:
                    # Yamel test
                    report.record_result(load_test(module_name, idref, mode))
                    # Python tests
                    env['ir.http']._clear_routing_map()     # force routing map to be rebuilt
                    report.record_result(odoo.modules.module.run_unit_tests(module_name, cr.dbname))

            processed_modules.append(package.name)

            ver = adapt_version(package.data['version'])
            # Set new modules and dependencies
            module.write({'state': 'installed', 'latest_version': ver})

            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)

        registry._init_modules.add(package.name)
        cr.commit()

    _logger.log(25, "%s modules loaded in %.2fs, %s queries", len(graph), time.time() - t0, odoo.sql_db.sql_counter - t0_sql)

    registry.clear_manual_fields()

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
        if not module_list:
            break
        graph.add_modules(cr, module_list, force)
        _logger.debug('Updating graph with %d more modules', len(module_list))
        loaded, processed = load_module_graph(cr, graph, progressdict, report=report, skip_modules=loaded_modules, perform_checks=perform_checks)
        processed_modules.extend(processed)
        loaded_modules.extend(loaded)
        if not processed:
            break
    return processed_modules

def load_modules(db, force_demo=False, status=None, update_module=False):
    initialize_sys_path()

    force = []
    if force_demo:
        force.append('demo')

    cr = db.cursor()
    try:
        if not odoo.modules.db.is_initialized(cr):
            _logger.info("init db")
            odoo.modules.db.initialize(cr)
            update_module = True # process auto-installed modules
            tools.config["init"]["all"] = 1
            tools.config['update']['all'] = 1
            if not tools.config['without_demo']:
                tools.config["demo"]['all'] = 1

        # This is a brand new registry, just created in
        # odoo.modules.registry.Registry.new().
        registry = odoo.registry(cr.dbname)
        env = api.Environment(cr, SUPERUSER_ID, {})

        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

        # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps)
        graph = odoo.modules.graph.Graph()
        graph.add_module(cr, 'base', force)
        if not graph:
            _logger.critical('module base cannot be loaded! (hint: verify addons-path)')
            raise ImportError('Module `base` cannot be loaded! (hint: verify addons-path)')

        # processed_modules: for cleanup step after install
        # loaded_modules: to avoid double loading
        report = registry._assertion_report
        loaded_modules, processed_modules = load_module_graph(cr, graph, status, perform_checks=update_module, report=report)

        load_lang = tools.config.pop('load_language')
        if load_lang or update_module:
            # some base models are used below, so make sure they are set up
            registry.setup_models(cr, partial=True)

        if load_lang:
            for lang in load_lang.split(','):
                tools.load_language(cr, lang)

        # STEP 2: Mark other modules to be loaded/updated
        if update_module:
            Module = env['ir.module.module']
            if ('base' in tools.config['init']) or ('base' in tools.config['update']):
                _logger.info('updating modules list')
                Module.update_list()

            _check_module_names(cr, itertools.chain(tools.config['init'].keys(), tools.config['update'].keys()))

            module_names = [k for k, v in tools.config['init'].items() if v]
            if module_names:
                modules = Module.search([('state', '=', 'uninstalled'), ('name', 'in', module_names)])
                if modules:
                    modules.button_install()

            module_names = [k for k, v in tools.config['update'].items() if v]
            if module_names:
                modules = Module.search([('state', '=', 'installed'), ('name', 'in', module_names)])
                if modules:
                    modules.button_upgrade()

            cr.execute("update ir_module_module set state=%s where name=%s", ('installed', 'base'))
            Module.invalidate_cache(['state'])


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

        registry.setup_models(cr)

        # STEP 4: Finish and cleanup installations
        if processed_modules:
            cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                if model in registry and not registry[model]._abstract and not registry[model]._transient:
                    _logger.warning('The model %s has no access rules, consider adding one. E.g. access_%s,access_%s,model_%s,,1,0,0,0',
                        model, model.replace('.', '_'), model.replace('.', '_'), model.replace('.', '_'))

            # Temporary warning while we remove access rights on osv_memory objects, as they have
            # been replaced by owner-only access rights
            cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
            for (model, name) in cr.fetchall():
                if model in registry and registry[model]._transient:
                    _logger.warning('The transient model %s (%s) should not have explicit access rules!', model, name)

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                if model in registry:
                    env[model]._check_removed_columns(log=True)
                else:
                    _logger.warning("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

            # Cleanup orphan records
            env['ir.model.data']._process_end(processed_modules)

        for kind in ('init', 'demo', 'update'):
            tools.config[kind] = {}

        cr.commit()

        # STEP 5: Uninstall modules to remove
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
                        py_module = sys.modules['odoo.addons.%s' % (pkg.name,)]
                        getattr(py_module, uninstall_hook)(cr, registry)

                Module = env['ir.module.module']
                Module.browse(modules_to_remove.values()).module_uninstall()
                # Recursive reload, should only happen once, because there should be no
                # modules to remove next time
                cr.commit()
                _logger.info('Reloading registry once more after uninstalling modules')
                api.Environment.reset()
                return odoo.modules.registry.Registry.new(cr.dbname, force_demo, status, update_module)

        # STEP 6: verify custom views on every model
        if update_module:
            View = env['ir.ui.view']
            custom_view_test = True
            for model in registry:
                if not View._validate_custom_views(model):
                    custom_view_test = False
                    _logger.error('invalid custom view(s) for model %s', model)
            report.record_result(custom_view_test)

        if report.failures:
            _logger.error('At least one test failed when loading the modules.')
        else:
            _logger.info('Modules loaded.')

        # STEP 8: call _register_hook on every model
        for model in env.values():
            model._register_hook()

        # STEP 9: Run the post-install tests
        cr.commit()

        t0 = time.time()
        t0_sql = odoo.sql_db.sql_counter
        if odoo.tools.config['test_enable']:
            if update_module:
                cr.execute("SELECT name FROM ir_module_module WHERE state='installed' and name = ANY(%s)", (processed_modules,))
            else:
                cr.execute("SELECT name FROM ir_module_module WHERE state='installed'")
            for module_name in cr.fetchall():
                report.record_result(odoo.modules.module.run_unit_tests(module_name[0], cr.dbname, position=runs_post_install))
            _logger.log(25, "All post-tested in %.2fs, %s queries", time.time() - t0, odoo.sql_db.sql_counter - t0_sql)
    finally:
        cr.close()
