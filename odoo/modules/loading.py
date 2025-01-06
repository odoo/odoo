# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules (also called addons) management.

"""
from __future__ import annotations

import itertools
import logging
import sys
import threading
import time
import typing
import warnings
import traceback

import odoo.sql_db
import odoo.tools.sql
import odoo.tools.translate
from odoo import SUPERUSER_ID, api, tools
from odoo.tools.misc import SENTINEL

from . import db as modules_db
from .graph import Graph
from .migration import MigrationManager
from .module import adapt_version, initialize_sys_path, load_openerp_module
from .registry import Registry

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from odoo.api import Environment
    from odoo.sql_db import BaseCursor
    from odoo.tests.result import OdooTestResult
    from .graph import Node

_logger = logging.getLogger(__name__)


def load_data(env: Environment, idref, mode: str, kind: str, package: Node) -> bool:
    """

    kind: data, demo, test, init_xml, update_xml, demo_xml.

    noupdate is False, unless it is demo data or it is csv data in
    init mode.

    :returns: Whether a file was loaded
    :rtype: bool
    """

    def _get_files_of_kind(kind: str) -> list[str]:
        if kind == 'demo':
            keys = ['demo_xml', 'demo']
        elif kind == 'data':
            keys = ['init_xml', 'update_xml', 'data']
        if isinstance(kind, str):
            keys = [kind]
        files: list[str] = []
        for k in keys:
            for f in package.data[k]:
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


def load_demo(env: Environment, package: Node, idref, mode: str) -> bool:
    """
    Loads demo data for the specified package.
    """
    if not package.should_have_demo():
        return False

    try:
        if package.data.get('demo') or package.data.get('demo_xml'):
            _logger.info("Module %s: loading demo", package.name)
            with env.cr.savepoint(flush=False):
                load_data(env(su=True), idref, mode, kind='demo', package=package)
        return True
    except Exception:  # noqa: BLE001
        # If we could not install demo data for this module
        _logger.warning(
            "Module %s demo data failed to install, installed without demo data",
            package.name, exc_info=True)

        todo = env.ref('base.demo_failure_todo', raise_if_not_found=False)
        Failure = env.get('ir.demo_failure')
        if todo and Failure is not None:
            todo.state = 'open'
            Failure.create({'module_id': package.id, 'error': traceback.format_exc()})
        return False


def force_demo(env: Environment) -> None:
    """
    Forces the `demo` flag on all modules, and installs demo data for all installed modules.
    """
    graph = Graph()
    env.cr.execute('UPDATE ir_module_module SET demo=True')
    env.cr.execute(
        "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade', 'to remove')"
    )
    module_list = [name for (name,) in env.cr.fetchall()]
    graph.add_modules(env.cr, module_list, ['demo'])

    for package in graph.packages():
        load_demo(env, package, {}, 'init')

    env['ir.module.module'].invalidate_model(['demo'])
    env['res.groups']._update_user_groups_view()


def load_module_graph(
    env: Environment,
    graph: Graph,
    status=SENTINEL,
    perform_checks: bool = True,
    skip_modules: Collection[str] = (),
    report: OdooTestResult | None = None,
    models_to_check: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Migrates+Updates or Installs all module nodes from ``graph``

       :param env:
       :param graph: graph of module nodes to load
       :param status: deprecated parameter, unused, left to avoid changing signature in 8.0
       :param perform_checks: whether module descriptors should be checked for validity (prints warnings
                              for same cases)
       :param skip_modules: optional list of module names (packages) which have previously been loaded and can be skipped
       :param report:
       :param set models_to_check:
       :return: list of modules that were installed or updated
    """
    if status is not SENTINEL:
        warnings.warn("Deprecated since 19.0, status is ignored", DeprecationWarning)
    if models_to_check is None:
        models_to_check = set()

    processed_modules = []
    loaded_modules = []
    registry = env.registry
    assert isinstance(env.cr, odoo.sql_db.Cursor), "Need for a real Cursor to load modules"
    migrations = MigrationManager(env.cr, graph)
    module_count = len(graph)
    _logger.info('loading %d modules...', module_count)

    # register, instantiate and initialize models for each modules
    t0 = time.time()
    loading_extra_query_count = odoo.sql_db.sql_counter
    loading_cursor_query_count = env.cr.sql_log_count

    models_updated = set()

    for index, package in enumerate(graph.packages(), 1):
        module_name = package.name
        module_id = package.id

        if module_name in skip_modules:
            continue

        module_t0 = time.time()
        module_cursor_query_count = env.cr.sql_log_count
        module_extra_query_count = odoo.sql_db.sql_counter

        needs_update = (
            hasattr(package, "init")
            or hasattr(package, "update")
            or package.state in ("to install", "to upgrade")
        )
        module_log_level = logging.DEBUG
        if needs_update:
            module_log_level = logging.INFO
        _logger.log(module_log_level, 'Loading module %s (%d/%d)', module_name, index, module_count)

        new_install = package.state == 'to install'
        if needs_update:
            if not new_install:
                if package.name != 'base':
                    registry.setup_models(env.cr)
                migrations.migrate_module(package, 'pre')
            if package.name != 'base':
                env.flush_all()

        load_openerp_module(package.name)

        if new_install:
            py_module = sys.modules['odoo.addons.%s' % (module_name,)]
            pre_init = package.info.get('pre_init_hook')
            if pre_init:
                registry.setup_models(env.cr)
                getattr(py_module, pre_init)(env)

        model_names = registry.load(env.cr, package)

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        loaded_modules.append(package.name)
        if needs_update:
            models_updated |= set(model_names)
            models_to_check -= set(model_names)
            registry.setup_models(env.cr)
            registry.init_models(env.cr, model_names, {'module': package.name}, new_install)
        elif package.state != 'to remove':
            # The current module has simply been loaded. The models extended by this module
            # and for which we updated the schema, must have their schema checked again.
            # This is because the extension may have changed the model,
            # e.g. adding required=True to an existing field, but the schema has not been
            # updated by this module because it's not marked as 'to upgrade/to install'.
            models_to_check |= set(model_names) & models_updated

        idref: dict = {}

        if needs_update:
            # Can't put this line out of the loop: ir.module.module will be
            # registered by init_models() above.
            module = env['ir.module.module'].browse(module_id)

            if perform_checks:
                module._check()

            if package.state == 'to upgrade':
                # upgrading the module information
                module.write(module.get_values_from_terp(package.data))
            load_data(env, idref, mode, kind='data', package=package)
            demo_loaded = package.dbdemo = load_demo(env, package, idref, mode)
            env.cr.execute('update ir_module_module set demo=%s where id=%s', (demo_loaded, module_id))
            module.invalidate_model(['demo'])

            migrations.migrate_module(package, 'post')

            # Update translations for all installed languages
            overwrite = tools.config["overwrite_existing_translations"]
            module._update_translations(overwrite=overwrite)

        if package.name is not None:
            registry._init_modules.add(package.name)

        if needs_update:
            if new_install:
                post_init = package.info.get('post_init_hook')
                if post_init:
                    getattr(py_module, post_init)(env)

            if mode == 'update':
                # validate the views that have not been checked yet
                env['ir.ui.view']._validate_module_views(module_name)

            # need to commit any modification the module's installation or
            # update made to the schema or data so the tests can run
            # (separately in their own transaction)
            env.cr.commit()
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
                        lines.append(f"{module_name}.access_{xmlid},access_{xmlid},{module_name}.model_{xmlid},base.group_user,1,0,0,0")
                    _logger.warning('\n'.join(lines))

        updating = tools.config.options['init'] or tools.config.options['update']
        test_time = 0.0
        test_queries = 0
        test_results = None
        if tools.config.options['test_enable'] and (needs_update or not updating):
            from odoo.tests import loader  # noqa: PLC0415
            suite = loader.make_suite([module_name], 'at_install')
            if suite.countTestCases():
                if not needs_update:
                    registry.setup_models(env.cr)
                # Python tests
                tests_t0, tests_q0 = time.time(), odoo.sql_db.sql_counter
                test_results = loader.run_suite(suite)
                assert report is not None, "Missing report during tests"
                report.update(test_results)
                test_time = time.time() - tests_t0
                test_queries = odoo.sql_db.sql_counter - tests_q0

                # tests may have reset the environment
                module = env['ir.module.module'].browse(module_id)

        if needs_update:
            processed_modules.append(package.name)

            ver = adapt_version(package.data['version'])
            # Set new modules and dependencies
            module.write({'state': 'installed', 'latest_version': ver})

            package.load_state = package.state
            package.load_version = package.installed_version
            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)
            module.env.flush_all()

        extra_queries = odoo.sql_db.sql_counter - module_extra_query_count - test_queries
        extras = []
        if test_queries:
            extras.append(f'+{test_queries} test')
        if extra_queries:
            extras.append(f'+{extra_queries} other')
        _logger.log(
            module_log_level, "Module %s loaded in %.2fs%s, %s queries%s",
            module_name, time.time() - module_t0,
            f' (incl. {test_time:.2f}s test)' if test_time else '',
            env.cr.sql_log_count - module_cursor_query_count,
            f' ({", ".join(extras)})' if extras else ''
        )
        if test_results and not test_results.wasSuccessful():
            _logger.error(
                "Module %s: %d failures, %d errors of %d tests",
                module_name, test_results.failures_count, test_results.errors_count,
                test_results.testsRun
            )

    _logger.runbot("%s modules loaded in %.2fs, %s queries (+%s extra)",
                   len(graph),
                   time.time() - t0,
                   env.cr.sql_log_count - loading_cursor_query_count,
                   odoo.sql_db.sql_counter - loading_extra_query_count)  # extra queries: testes, notify, any other closed cursor

    return loaded_modules, processed_modules


def _check_module_names(cr: BaseCursor, module_names: Iterable[str]) -> None:
    mod_names = set(module_names)
    if 'base' in mod_names:
        # ignore dummy 'all' module
        mod_names.discard('all')
    if mod_names:
        cr.execute("SELECT count(id) AS count FROM ir_module_module WHERE name in %s", (tuple(mod_names),))
        row = cr.fetchone()
        assert row is not None  # for typing
        if row[0] != len(mod_names):
            # find out what module name(s) are incorrect:
            cr.execute("SELECT name FROM ir_module_module")
            incorrect_names = mod_names.difference([x['name'] for x in cr.dictfetchall()])
            _logger.warning('invalid module names, ignored: %s', ", ".join(incorrect_names))


def load_marked_modules(
    env: Environment,
    graph: Graph,
    states: Collection[str],
    force: list[str],
    progressdict: None,
    report: OdooTestResult | None,
    loaded_modules: list[str],
    perform_checks: bool,
    models_to_check: set[str] | None = None,
) -> list[str]:
    """Loads modules marked with ``states``, adding them to ``graph`` and
       ``loaded_modules`` and returns a list of installed/upgraded modules."""

    if progressdict is not None:
        warnings.warn("Deprecated since 19.0, progressdict is ignored and should be set to None", DeprecationWarning)
    if models_to_check is None:
        models_to_check = set()

    processed_modules: list[str] = []
    while True:
        env.cr.execute("SELECT name from ir_module_module WHERE state IN %s", (tuple(states),))
        module_list = [name for (name,) in env.cr.fetchall() if name not in graph]
        if not module_list:
            break
        graph.add_modules(env.cr, module_list, force)
        _logger.debug('Updating graph with %d more modules', len(module_list))
        loaded, processed = load_module_graph(
            env,
            graph,
            report=report,
            skip_modules=loaded_modules,
            perform_checks=perform_checks,
            models_to_check=models_to_check,
        )
        processed_modules.extend(processed)
        loaded_modules.extend(loaded)
        if not processed:
            break
    return processed_modules


def load_modules(registry: Registry, force_demo: bool = False, status: None = None, update_module: bool = False) -> None:
    """ Load the modules for a registry object that has just been created.  This
        function is part of Registry.new() and should not be used anywhere else.
    """
    if status is not None:
        warnings.warn("Deprecated since 19.0, status is deprecated, do not set it")
    initialize_sys_path()

    force: list[str] = []
    if force_demo:
        force.append('demo')

    models_to_check: set[str] = set()

    with registry.cursor() as cr:
        # prevent endless wait for locks on schema changes (during online
        # installs) if a concurrent transaction has accessed the table;
        # connection settings are automatically reset when the connection is
        # borrowed from the pool
        cr.execute("SET SESSION lock_timeout = '15s'")
        if not modules_db.is_initialized(cr):
            if not update_module:
                _logger.error("Database %s not initialized, you can force it with `-i base`", cr.dbname)
                return
            _logger.info("init db")
            modules_db.initialize(cr)
            update_module = True # process auto-installed modules
            tools.config["init"]["all"] = 1
            if not tools.config['without_demo']:
                tools.config["demo"]['all'] = 1

        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

        # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps)
        graph = Graph()
        graph.add_module(cr, 'base', force)
        if not graph:
            _logger.critical('module base cannot be loaded! (hint: verify addons-path)')
            raise ImportError('Module `base` cannot be loaded! (hint: verify addons-path)')

        if update_module and tools.sql.table_exists(cr, 'ir_model_fields'):
            # determine the fields which are currently translated in the database
            cr.execute("SELECT model || '.' || name FROM ir_model_fields WHERE translate IS TRUE")
            registry._database_translated_fields = {row[0] for row in cr.fetchall()}

        # processed_modules: for cleanup step after install
        # loaded_modules: to avoid double loading
        report = registry._assertion_report
        env = api.Environment(cr, SUPERUSER_ID, {})
        loaded_modules, processed_modules = load_module_graph(
            env,
            graph,
            perform_checks=update_module,
            report=report,
            models_to_check=models_to_check,
        )

        load_lang = tools.config._cli_options.pop('load_language', None)
        if load_lang or update_module:
            # some base models are used below, so make sure they are set up
            registry.setup_models(cr)

        if load_lang:
            for lang in load_lang.split(','):
                tools.translate.load_language(cr, lang)

        # STEP 2: Mark other modules to be loaded/updated
        if update_module:
            Module = env['ir.module.module']
            _logger.info('updating modules list')
            Module.update_list()

            _check_module_names(cr, itertools.chain(tools.config['init'], tools.config['update']))

            module_names = [k for k, v in tools.config['init'].items() if v]
            if module_names:
                modules = Module.search([('state', '=', 'uninstalled'), ('name', 'in', module_names)])
                if modules:
                    modules.button_install()

            module_names = [k for k, v in tools.config['update'].items() if v]
            if module_names:
                modules = Module.search([('state', 'in', ('installed', 'to upgrade')), ('name', 'in', module_names)])
                if modules:
                    modules.button_upgrade()

            env.flush_all()
            cr.execute("update ir_module_module set state=%s where name=%s", ('installed', 'base'))
            Module.invalidate_model(['state'])

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
            processed_modules += load_marked_modules(
                env, graph, ['installed', 'to upgrade', 'to remove'],
                force, None, report, loaded_modules, update_module, models_to_check)
            if update_module:
                processed_modules += load_marked_modules(
                    env, graph, ['to install'],
                    force, None, report, loaded_modules, update_module, models_to_check)

        if update_module:
            # set up the registry without the patch for translated fields
            database_translated_fields = registry._database_translated_fields
            registry._database_translated_fields = set()
            registry.setup_models(cr)
            # determine which translated fields should no longer be translated,
            # and make their model fix the database schema
            models_to_untranslate = set()
            for full_name in database_translated_fields:
                model_name, field_name = full_name.rsplit('.', 1)
                if model_name in registry:
                    field = registry[model_name]._fields.get(field_name)
                    if field and not field.translate:
                        _logger.debug("Making field %s non-translated", field)
                        models_to_untranslate.add(model_name)
            registry.init_models(cr, list(models_to_untranslate), {'models_to_check': True})

        registry.loaded = True
        registry.setup_models(cr)

        # check that all installed modules have been loaded by the registry
        Module = env['ir.module.module']
        modules = Module.search_fetch(Module._get_modules_to_load_domain(), ['name'], order='name')
        missing = [name for name in modules.mapped('name') if name not in graph]
        if missing:
            _logger.error("Some modules are not loaded, some dependencies or manifest may be missing: %s", missing)

        # STEP 3.5: execute migration end-scripts
        migrations = MigrationManager(cr, graph)
        for package in graph.packages():
            migrations.migrate_module(package, 'end')

        # check that new module dependencies have been properly installed after a migration/upgrade
        cr.execute("SELECT name from ir_module_module WHERE state IN ('to install', 'to upgrade')")
        module_list = [name for (name,) in cr.fetchall()]
        if module_list:
            _logger.error("Some modules have inconsistent states, some dependencies may be missing: %s", sorted(module_list))

        # STEP 3.6: apply remaining constraints in case of an upgrade
        registry.finalize_constraints()

        # STEP 4: Finish and cleanup installations
        if processed_modules:

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                if model in registry:
                    env[model]._check_removed_columns(log=True)
                elif _logger.isEnabledFor(logging.INFO):    # more an info that a warning...
                    _logger.runbot("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

            # Cleanup orphan records
            env['ir.model.data']._process_end(processed_modules)
            env.flush_all()

        for kind in ('init', 'demo', 'update'):
            tools.config[kind] = {}

        # STEP 5: Uninstall modules to remove
        if update_module:
            # Remove records referenced from ir_model_data for modules to be
            # removed (and removed the references from ir_model_data).
            cr.execute("SELECT name, id FROM ir_module_module WHERE state=%s", ('to remove',))
            modules_to_remove = dict(cr.fetchall())
            if modules_to_remove:
                pkgs = reversed([p for p in graph.packages() if p.name in modules_to_remove])
                for pkg in pkgs:
                    uninstall_hook = pkg.info.get('uninstall_hook')
                    if uninstall_hook:
                        py_module = sys.modules['odoo.addons.%s' % (pkg.name,)]
                        getattr(py_module, uninstall_hook)(env)
                        env.flush_all()

                Module = env['ir.module.module']
                Module.browse(modules_to_remove.values()).module_uninstall()
                # Recursive reload, should only happen once, because there should be no
                # modules to remove next time
                cr.commit()
                _logger.info('Reloading registry once more after uninstalling modules')
                registry = Registry.new(
                    cr.dbname, force_demo, update_module=update_module
                )
                cr.reset()
                registry.check_tables_exist(cr)
                cr.commit()
                return

        # STEP 5.5: Verify extended fields on every model
        # This will fix the schema of all models in a situation such as:
        #   - module A is loaded and defines model M;
        #   - module B is installed/upgraded and extends model M;
        #   - module C is loaded and extends model M;
        #   - module B and C depend on A but not on each other;
        # The changes introduced by module C are not taken into account by the upgrade of B.
        if models_to_check:
            registry.init_models(cr, list(models_to_check), {'models_to_check': True})

        # STEP 6: verify custom views on every model
        if update_module:
            env['res.groups']._update_user_groups_view()
            View = env['ir.ui.view']
            for model in registry:
                try:
                    View._validate_custom_views(model)
                except Exception as e:
                    _logger.warning('invalid custom view(s) for model %s: %s', model, e)

        if not registry._assertion_report or registry._assertion_report.wasSuccessful():
            _logger.info('Modules loaded.')
        else:
            _logger.error('At least one test failed when loading the modules.')


        # STEP 8: save installed/updated modules for post-install tests and _register_hook
        registry.updated_modules += processed_modules

        # STEP 9: call _register_hook on every model
        # This is done *exactly once* when the registry is being loaded. See the
        # management of those hooks in `Registry.setup_models`: all the calls to
        # setup_models() done here do not mess up with hooks, as registry.ready
        # is False.
        for model in env.values():
            model._register_hook()
        env.flush_all()


def reset_modules_state(db_name: str) -> None:
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
