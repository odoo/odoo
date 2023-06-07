# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules (also called addons) management.

"""
import collections
import itertools
import logging
import sys
import threading
import time

from typing import Dict

import odoo
import odoo.modules.db
import odoo.modules.migration
import odoo.modules.registry
from .. import SUPERUSER_ID, api, tools
from ..tools import OrderedSet
from .module import adapt_version, initialize_sys_path, load_openerp_module
from odoo.modules.graph import PackageGraph

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')


def load_data(env, idref, mode, kind, package):
    """

    kind: data, demo, test, init_xml, update_xml, demo_xml.

    noupdate is False, unless it is demo data or it is csv data in
    init mode.

    :returns: Whether a file was loaded
    :rtype: bool
    """

    def _get_files_of_kind(kind):
        if kind == 'demo':
            keys = ['demo_xml', 'demo']
        elif kind == 'data':
            keys = ['init_xml', 'update_xml', 'data']
        if isinstance(kind, str):
            keys = [kind]
        files = []
        for k in keys:
            for f in package.manifest[k]:
                if f in files:
                    _logger.warning("File %s is imported twice in module %s %s", f, package.name, kind)
                files.append(f)
                if k.endswith('_xml') and not (k == 'init_xml' and not f.endswith('.xml')):
                    # init_xml, update_xml and demo_xml are deprecated except
                    # for the case of init_xml with csv and sql files as
                    # we can't specify noupdate for those file.
                    correct_key = 'demo' if k.count('demo') else 'data'
                    _logger.warning(
                        "module %s: key '%s' is deprecated in favor of '%s' for file '%s'.",
                        package.name, k, correct_key, f
                    )
        return files

    filename = None
    try:
        if kind in ('demo', 'test'):
            threading.current_thread().testing = True
        for filename in _get_files_of_kind(kind):
            _logger.info("loading %s/%s", package.name, filename)
            noupdate = False
            if kind in ('demo', 'demo_xml') or (filename.endswith('.csv') and kind in ('init', 'init_xml')):
                noupdate = True
            tools.convert_file(env, package.name, filename, idref, mode, noupdate, kind)
    finally:
        if kind in ('demo', 'test'):
            threading.current_thread().testing = False

    return bool(filename)

def load_demo(env, package, idref, mode):
    """
    Loads demo data for the specified package.
    """
    loaded = False
    if package.demo_installable():
        try:
            if package.manifest.get('demo') or package.manifest.get('demo_xml'):
                _logger.info("Module %s: loading demo", package.name)
                with env.cr.savepoint(flush=False):
                    load_data(env, idref, mode, kind='demo', package=package)
            loaded = True
        except Exception as e:
            # If we could not install demo data for this module
            _logger.warning(
                "Module %s demo data failed to install, installed without demo data",
                package.name, exc_info=True)

            todo = env.ref('base.demo_failure_todo', raise_if_not_found=False)
            Failure = env.get('ir.demo_failure')
            if todo and Failure is not None:
                todo.state = 'open'
                Failure.create({'module_id': package.id, 'error': str(e)})

    if loaded != package.dbdemo:
        package.dbdemo = loaded
        env['ir.module.module'].invalidate_model(['demo'])
        env.cr.execute('UPDATE ir_module_module SET demo = %s WHERE id = %s', (loaded, package.id))


def force_demo(env):
    """
    Forces the `demo` flag on all modules, and installs demo data for all installed modules.
    """
    graph = PackageGraph(env.cr)
    env.cr.execute('UPDATE ir_module_module SET demo=True')
    env.cr.execute(
        "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade', 'to remove')"
    )
    module_list = [name for (name,) in env.cr.fetchall()]
    graph.add(module_list)

    for package in graph:
        load_demo(env, package, {}, 'init')

    env['res.groups']._update_user_groups_view()


def _load_module(env, package) -> OrderedSet:
    registry = env.registry

    load_openerp_module(package.name)
    model_names = registry.load(env.cr, package)
    registry.all_models_set_up = False

    registry._init_modules.add(package.name)

    return model_names

def _install_module(env, package) -> OrderedSet:
    registry = env.registry
    module_name = package.name
    module_id = package.id

    load_openerp_module(package.name)

    py_module = sys.modules['odoo.addons.%s' % (module_name,)]
    pre_init = package.manifest.get('pre_init_hook')
    if pre_init:
        if not registry.all_models_set_up:
            registry.setup_models(env.cr)
        getattr(py_module, pre_init)(env)

    model_names = registry.load(env.cr, package)
    registry.setup_models(env.cr)
    registry.all_models_set_up = True
    registry.init_models(env.cr, model_names, {'module': package.name}, install=True)

    module = env['ir.module.module'].browse(module_id)

    module._check()

    idref = {}
    load_data(env, idref, 'init', kind='data', package=package)
    if not tools.config['without_demo'] or package.dbdemo:
        load_demo(env, package, idref, 'init')

    # Update translations for all installed languages
    overwrite = odoo.tools.config["overwrite_existing_translations"]
    module._update_translations(overwrite=overwrite)

    registry._init_modules.add(package.name)

    post_init = package.manifest.get('post_init_hook')
    if post_init:
        getattr(py_module, post_init)(env)

    env.flush_all()
    _check_access_rules(env, module_name, model_names)

    module = env['ir.module.module'].browse(module_id)
    package.installed_version = adapt_version(package.manifest['version'])
    package.state = 'installed'
    # Set new modules and dependencies
    module.write({'state': 'installed', 'latest_version': package.installed_version})
    env.cr.commit()
    return model_names

def _upgrade_module(env, package, migrations) -> OrderedSet:
    registry = env.registry
    module_name = package.name
    module_id = package.id

    if not registry.all_models_set_up:
        registry.setup_models(env.cr)
    migrations.migrate_module(package, 'pre')

    load_openerp_module(package.name)

    model_names = registry.load(env.cr, package)
    registry.setup_models(env.cr)
    registry.all_models_set_up = True
    registry.init_models(env.cr, model_names, {'module': package.name}, install=False)

    module = env['ir.module.module'].browse(module_id)

    module._check()

    # upgrading the module information
    module.write(module.get_values_from_terp(package.manifest))

    idref = {}
    load_data(env, idref, 'update', kind='data', package=package)
    if package.dbdemo:
        load_demo(env, package, idref, 'update')

    migrations.migrate_module(package, 'post')

    # Update translations for all installed languages
    overwrite = odoo.tools.config["overwrite_existing_translations"]
    module._update_translations(overwrite=overwrite)

    registry._init_modules.add(package.name)

    env.flush_all()
    # validate the views that have not been checked yet
    env['ir.ui.view']._validate_module_views(module_name)

    _check_access_rules(env, module_name, model_names)

    module = env['ir.module.module'].browse(module_id)
    package.installed_version = adapt_version(package.manifest['version'])
    package.state = 'installed'
    # Set new modules and dependencies
    module.write({'state': 'installed', 'latest_version': package.installed_version})
    env.cr.commit()
    return model_names

def _check_access_rules(env, module_name, model_names):
    registry = env.registry
    concrete_models = [model for model in model_names if not registry[model]._abstract]
    if concrete_models:
        env.cr.execute("""
                        SELECT model FROM ir_model 
                        WHERE id NOT IN (SELECT DISTINCT model_id FROM ir_model_access) AND model IN %s
                    """, [tuple(concrete_models)])
        models = [model for [model] in env.cr.fetchall()]
        if models:
            lines = [
                f"The models {models} have no access rules in module {module_name}, consider adding some, like:",
                "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
            ]
            for model in models:
                xmlid = model.replace('.', '_')
                lines.append(
                    f"{module_name}.access_{xmlid},access_{xmlid},{module_name}.model_{xmlid},base.group_user,1,0,0,0")
            _logger.warning('\n'.join(lines))

def _test_module(env, module_name):
    test_queries = test_time = 0
    test_results = None
    loader = odoo.tests.loader
    suite = loader.make_suite([module_name], 'at_install')
    if suite.countTestCases():
        if not env.registry.all_models_set_up:
            env.registry.setup_models(env.cr)
        # need to commit any modification the module's installation or
        # update made to the schema or data so the tests can run
        # (separately in their own transaction)
        env.cr.commit()
        # Python tests
        env['ir.http']._clear_routing_map()  # force routing map to be rebuilt

        tests_t0, tests_q0 = time.time(), odoo.sql_db.sql_counter
        test_results = loader.run_suite(suite, module_name)
        test_time = time.time() - tests_t0
        test_queries = odoo.sql_db.sql_counter - tests_q0

        if not test_results.wasSuccessful():
            _logger.error(
                "Module %s: %d failures, %d errors of %d tests",
                module_name, test_results.failures_count, test_results.errors_count,
                test_results.testsRun
            )

    return test_results, test_queries, test_time


def load_module_graph(env, graph: PackageGraph, force_test: bool = False) -> OrderedSet:
    """Load, upgrade and install all module nodes from ``graph`` for the registry ``env.registry``

           :param env: Odoo environment with the registry to be loaded
           :param graph: ordered packages to be loaded/upgraded/installed
           :param force_test: if True, all modules will be tested

           :return: OrderedSet of module names that were installed or upgraded during this call
        """

    update_module = graph._update_module
    registry = env.registry

    # models_to_fixup
    # a model is marked models_to_fixup and re-inited to promise the ** eventual consistency **
    # between the registry and the database if
    #
    # Scenario 1. it is updated and loaded but not updated again
    #    because while loading an 'installed' module, its models are be inited
    #
    #    Note: Strictly speaking, it should be re-inited before the next 'to install'/'to update' module, since update
    #          hooks may use the model's ORM. But we sacrifice some correctness while updating for performance, since it
    #          rarely cause problems
    #
    #          the corner case may only cause problems when you upgrade some(but not all) modules
    #          For example:
    # 	            there are some modules with loading order
    # 	            module_A -> module_B -> module_C -> module_D
    #
    # 	            module_B depends on module_A
    # 	            module_C depends on module_A
    # 	            module_D depends on module_C
    #
    # 	            field_X is defined in module_A, module_B, module_C, module_D with
    # 		            not specified `required` for module_A
    # 		            `required=True` for module_B
    # 		            `required=False` for module_C
    # 		            not specified `required` for module_D
    #
    # 	        for sake of the loading order, the field_X should be `required=False` specified by module_C
    # 	        when module_B and module_D are 'to upgrade',
    # 	        after module_B is upgraded, the column for field_X has not-null constraint
    # 	        ** if we don't re-init the model for field_X after loading module_C **,
    # 	        while upgrading module_D, module_D may import some data which has empty field_X and cause error
    #
    # Scenario 2. it is updated and a module which has larger loading order has been updated/loaded before this module
    #    because the updating order when update_module is True may be different from the loading order when the
    #    update_module is False
    #
    # Scenario 3. its module is `to remove`
    #    caused by the trick that removing a module means load all other modules again without the module
    #
    updated_models = OrderedSet()  # models whose modules are installed/upgraded
    updated_loaded_models = OrderedSet()  # models which are updated and then loaded but not updated again
    loaded_models: Dict[(int, str), OrderedSet] = {}  # {loading_sort_key: models}
    largest_loading_sort_key = ()

    updated_modules = OrderedSet()

    if update_module:
        migrations = odoo.modules.migration.MigrationManager(env.cr, graph)
    module_count = len(graph)
    _logger.info('loading %d modules...', module_count)

    # register, instantiate and initialize models for each modules
    t0 = time.time()
    loading_extra_query_count = odoo.sql_db.sql_counter
    loading_cursor_query_count = env.cr.sql_log_count


    for index, package in enumerate(graph, 1):
        module_name = package.name

        if module_name in env.registry._init_modules:
            continue

        module_t0 = time.time()
        module_cursor_query_count = env.cr.sql_log_count
        module_extra_query_count = odoo.sql_db.sql_counter

        need_update = update_module and package.state in ("to install", "to upgrade")
        need_test = tools.config.options['test_enable'] and (need_update or force_test)  # CWG: TBD

        module_log_level = logging.INFO if need_update else logging.DEBUG
        _logger.log(module_log_level, 'Loading module %s (%d/%d)', module_name, index, module_count)

        if need_update:
            if package.state == 'to install':
                model_names = _install_module(env, package)
            else:  # 'to upgrade'
                model_names = _upgrade_module(env, package, migrations)
            updated_models |= model_names
            updated_loaded_models -= model_names
            updated_modules.add(package.name)
            if largest_loading_sort_key > package.loading_sort_key:  # shortcut to avoid the set operation below
                # scenario 2 for models_to_fixup
                registry.models_to_fixup |= model_names & OrderedSet.union(*(
                    _model_names
                    for loading_sort_key, _model_names in loaded_models.items()
                    if loading_sort_key > package.loading_sort_key
                ))
        else:
            model_names = _load_module(env, package)  # returns an OrderedSet
            updated_loaded_models |= updated_models & model_names
            if update_module and package.state == 'to remove':
                # scenario 3 for models_to_fixup
                registry.models_to_fixup |= model_names

        if update_module:
            loaded_models[(package.depth, package.name)] = model_names
            largest_loading_sort_key = max(largest_loading_sort_key, package.loading_sort_key)

        extras = []
        test_time = 0
        if need_test:
            test_results, test_query_count, test_time = _test_module(env, module_name)
            module_extra_query_count += test_query_count
            if test_results:
                registry._assertion_report.update(test_results)
            if test_query_count:
                extras.append(f'+{test_query_count} test')
        other_query_count = odoo.sql_db.sql_counter - module_extra_query_count
        if other_query_count:
            extras.append(f'+{other_query_count} other')

        _logger.log(
            module_log_level, "Module %s loaded in %.2fs%s, %s queries%s",
            module_name, time.time() - module_t0,
            f' (incl. {test_time:.2f}s test)' if test_time else '',
                         env.cr.sql_log_count - module_cursor_query_count,
            f' ({", ".join(extras)})' if extras else ''
        )

    registry.models_to_fixup |= updated_loaded_models  # scenario 1 for models_to_fixup

    _logger.runbot("%s modules loaded in %.2fs, %s queries (+%s extra)",
                   len(graph),
                   time.time() - t0,
                   env.cr.sql_log_count - loading_cursor_query_count,
                   odoo.sql_db.sql_counter - loading_extra_query_count)  # extra queries: testes, notify, any other closed cursor

    return updated_modules


def _update_ir_module_module(env, upgrade_module_names, install_module_names):
    """ update modules' dependency, state"""
    Module = env['ir.module.module']

    if upgrade_module_names:
        domain = [('state', 'in', ('installed', 'to upgrade'))]
        if 'all' in upgrade_module_names:
            domain.append(('name', '!=', 'base'))
        else:
            domain.append(('name', 'in', upgrade_module_names))
        modules = Module.search(domain)
        if modules:
            modules.button_upgrade()
        ignored_module_names = set(upgrade_module_names) - set(modules.mapped('name')) - {'all'}
        if ignored_module_names:
            _logger.warning(
                'modules: %s are ignored for upgrading, because they were not installed, they are going to be removed or their names are invalid',
                ", ".join(ignored_module_names))

    if install_module_names:
        modules = Module.search([('state', 'in', ('uninstalled', 'to install')), ('name', 'in', install_module_names)])
        if modules:
            modules.button_install()
        ignored_module_names = set(install_module_names) - set(modules.mapped('name'))
        if ignored_module_names:
            _logger.warning(
                'modules: %s are ignored for installing, because they have been installed or their names are invalid',
                ", ".join(ignored_module_names))

    env.flush_all()

def _get_models_to_untranslate(env) -> OrderedSet:
    registry = env.registry
    # set up the registry without the patch for translated fields
    database_translated_fields = registry._database_translated_fields
    registry._database_translated_fields = None
    registry.setup_models(env.cr)
    # determine which translated fields should no longer be translated,
    # and make their model fix the database schema
    models_to_untranslate = OrderedSet()
    for full_name in database_translated_fields:
        model_name, field_name = full_name.rsplit('.', 1)
        if model_name in registry:
            field = registry[model_name]._fields.get(field_name)
            if field and not field.translate:
                _logger.debug("Making field %s non-translated", field)
                models_to_untranslate.add(model_name)
    return models_to_untranslate

def _fixup_models(env):
    registry = env.registry
    registry.init_models(
        env.cr,
        [model_name for model_name in registry.models_to_fixup if model_name in env],
        {'models_to_fixup': True}
    )
    registry.models_to_fixup = OrderedSet()

def _check_modules(env):
    Module = env['ir.module.module']

    # check that all installed modules have been loaded by the registry
    modules = Module.search(Module._get_modules_to_load_domain(), order='name')
    missing = [name for name in modules.mapped('name') if name not in env.registry._init_modules]
    if missing:
        _logger.error("Some modules are not loaded, some dependencies or manifest may be missing: %s", missing)

    # check that new module dependencies have been properly installed after a migration/upgrade
    modules = Module.search([('name', 'in', ('to install', 'to upgrade', 'to remove'))], order='name')
    if modules:
        _logger.error("Some modules have inconsistent states, some dependencies may be missing: %s", modules.mapped('name'))

def _cleanup(env):
    env.cr.execute("SELECT model from ir_model")
    for (model,) in env.cr.fetchall():
        if model in env.registry:
            env[model]._check_removed_columns(log=True)
        elif _logger.isEnabledFor(logging.INFO):  # more an info that a warning...
            _logger.runbot("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

    # Cleanup orphan records
    env['ir.model.data']._process_end(env.registry.updated_modules)
    env.flush_all()

def _check_views(env):
    """ verify custom views on every model """
    registry = env.registry
    View = env['ir.ui.view']
    for model in registry:
        try:
            View._validate_custom_views(model)
        except Exception as e:
            _logger.warning('invalid custom view(s) for model %s: %s', model, tools.ustr(e))

def load_modules(
        registry,
        update_module: bool = False,
        force_test: bool = False,
        force_demo_: bool = False
) -> None:
    """ Load the modules for a registry object that has just been created.  This
        function is part of Registry.new() and should not be used anywhere else.

        Args:
            dbname (str): the name of database
            update_module (bool, optional): If True, init, upgrade and remove modules while loading
            force_test (bool, optional): force_test at_install tests
            force_demo_ (bool, optional): If True, forcely load demo for all updated modules
                deprecated: it will mark the demo field of all modules to True, which will install/update demo data for
                all modules when they are updated in the future
    """
    initialize_sys_path()
    updated_modules = OrderedSet()
    assert registry.loaded is False
    with registry.cursor() as cr:
        # prevent endless wait for locks on schema changes (during online
        # installs) if a concurrent transaction has accessed the table;
        # connection settings are automatically reset when the connection is
        # borrowed from the pool
        cr.execute("SET SESSION lock_timeout = '15s'")
        if not odoo.modules.db.is_initialized(cr):
            if not update_module:
                _logger.error("Database %s not initialized, you can force it with `-i base`", cr.dbname)
                raise Exception()
            _logger.info("init db")
            odoo.modules.db.initialize(cr)
        elif update_module and registry._database_translated_fields is None:
            # determine the fields which are currently translated in the database
            cr.execute("SELECT model || '.' || name FROM ir_model_fields WHERE translate IS TRUE")
            registry._database_translated_fields = {row[0] for row in cr.fetchall()}

        # STEP 1: load base (must be done before module dependencies can be computed for later steps)
        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("UPDATE ir_module_module SET state = %s WHERE name = %s AND state = %s", ('to upgrade', 'base', 'installed'))
        if force_demo_:
            cr.execute("UPDATE ir_module_module SET demo = %s WHERE name = %s", (True, 'base'))
        graph = PackageGraph(cr, update_module=update_module)
        graph.add(['base'])
        if not graph:
            _logger.critical('module base cannot be loaded! (hint: verify addons-path)')
            raise ImportError('Module `base` cannot be loaded! (hint: verify addons-path)')

        env = api.Environment(cr, SUPERUSER_ID, {})
        updated_modules |= load_module_graph(env, graph, force_test=force_test)
        registry.updated_modules |= updated_modules

        load_lang = tools.config['load_language']
        tools.config['load_language'] = None
        if load_lang:
            if not registry.all_models_set_up:
                # some base models are used below, so make sure they are set up
                registry.setup_models(cr)
            for lang in load_lang.split(','):
                tools.load_language(cr, lang)

        # STEP 2: mark non-base modules to install/upgrade
        if update_module:
            upgrade_module_names = [k for k, v in tools.config['update'].items() if v and k != 'base']
            install_module_names = [k for k, v in tools.config['init'].items() if v and k != 'base']
            if (upgrade_module_names or install_module_names) and not registry.all_models_set_up:
                registry.setup_models(cr)
            if not upgrade_module_names and install_module_names:
                env['ir.module.module'].update_list()
            _update_ir_module_module(env, upgrade_module_names, install_module_names)
            if force_demo_:
                force_demo(env)

        # STEP 3: load non-base modules
        states = ('installed', 'to upgrade', 'to remove', 'to install') if update_module else ('installed', 'to upgrade', 'to remove')
        env.cr.execute("SELECT name from ir_module_module WHERE state IN %s", (states,))
        module_list = [name for (name,) in env.cr.fetchall() if name not in graph]
        graph.add(module_list)
        _logger.debug('Updating graph with %d more modules', len(module_list))

        updated_modules |= load_module_graph(env, graph, force_test=force_test)
        registry.updated_modules |= updated_modules

        registry.loaded = True
        if not registry.all_models_set_up:
            registry.setup_models(cr)

        tools.config['init'] = {}
        tools.config['update'] = {}

        if updated_modules:

            # STEP 4: execute migration end-scripts
            migrations = odoo.modules.migration.MigrationManager(cr, graph)
            for package in graph:
                migrations.migrate_module(package, 'end')

            # STEP 5: apply remaining constraints in case of an upgrade
            registry.finalize_constraints()

            # STEP 6: check if there are modules to update
            registry.has_modules_to_update = env['ir.module.module'].search_count([
                ('state', 'in', ('to upgrade', 'to install')),
                ('name', 'not in', tuple(registry._init_modules))
            ], limit=1)

            if registry.has_modules_to_update or not graph.is_loading_order_sorted:
                return

        if update_module:
            # STEP 7: uninstall modules to remove
            # Remove records referenced from ir_model_data for modules to be
            # removed (and removed the references from ir_model_data).
            packages_to_remove = [p for p in reversed(graph) if p.state == 'to remove']
            if packages_to_remove:
                registry.has_modules_removed = True
                for package in packages_to_remove:
                    uninstall_hook = package.manifest.get('uninstall_hook')
                    if uninstall_hook:
                        py_module = sys.modules['odoo.addons.%s' % (package.name,)]
                        getattr(py_module, uninstall_hook)(env)
                        env.flush_all()

                Module = env['ir.module.module']
                Module.browse([package.id for package in packages_to_remove]).module_uninstall()
                _logger.info('Reloading registry once more after uninstalling modules')
                return

        # STEP 8: fixup models
        if registry._database_translated_fields is not None:
            registry.models_to_fixup |= _get_models_to_untranslate(env)
        if registry.models_to_fixup:
            _fixup_models(env)

        if registry.has_modules_removed:
            registry.check_tables_exist(cr)

        if registry.updated_modules:
            _cleanup(env)
            env['res.groups']._update_user_groups_view()

        # STEP 9: check loading
            _check_views(env)

        _check_modules(env)

        # STEP 10: call _register_hook on every model
        # This is done *exactly once* when the registry is being loaded. See the
        # management of those hooks in `Registry.setup_models`: all the calls to
        # setup_models() done here do not mess up with hooks, as registry.ready
        # is False.
        for model in env.values():
            model._register_hook()

        if registry._assertion_report.wasSuccessful():
            _logger.info('Modules loaded.')
        else:
            _logger.error('At least one test failed when loading the modules.')

        registry.ready = True


def reset_modules_state(db_name):
    """
    Resets modules flagged as "to x" to their original state
    """
    # Warning, this function was introduced in response to commit 763d714
    # which locks cron jobs for dbs which have modules marked as 'to %'.
    # The goal of this function is to be called ONLY when module
    # installation/upgrade/uninstallation fails, which is the only known case
    # for which modules can stay marked as 'to %' for an indefinite amount
    # of time
    db = odoo.sql_db.db_connect(db_name)
    with db.cursor() as cr:
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module'")
        if not cr.fetchall():
            _logger.info('skipping reset_modules_state, ir_module_module table does not exists')
            return
        cr.execute(
            "UPDATE ir_module_module SET state='installed' WHERE state IN ('to remove', 'to upgrade')"
        )
        cr.execute(
            "UPDATE ir_module_module SET state='uninstalled' WHERE state='to install'"
        )
        _logger.warning("Transient module states were reset")
