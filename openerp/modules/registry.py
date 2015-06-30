# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Models registries.

"""
import itertools
import logging
import os
import sys
import threading
import time

from collections import Mapping, defaultdict
from contextlib import closing

import openerp
from .. import SUPERUSER_ID
from ..tools import assertion_report, classproperty, config, \
                    lazy_property, topological_sort, OrderedSet,\
                    convert_file
from ..tools.lru import LRU

from . import migration
from .module import initialize_sys_path, runs_post_install, run_unit_tests, \
    load_openerp_module, init_models, adapt_version

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('openerp.tests')

class Registry(Mapping):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model
    instances. There is one registry instance per database.

    """

    def __init__(self, db_name):
        super(Registry, self).__init__()
        self.models = {}    # model name/model instance mapping
        self._sql_error = {}
        self._store_function = {}
        self._pure_function_fields = {}         # {model: [field, ...], ...}
        self._init = True
        self._init_parent = {}
        self._assertion_report = assertion_report.assertion_report()
        self._fields_by_model = None

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()

        self.db_name = db_name
        self._db = openerp.sql_db.db_connect(db_name)

        # special cursor for test mode; None means "normal" mode
        self.test_cr = None

        # Indicates that the registry is 
        self.ready = False

        # Inter-process signaling (used only when openerp.multi_process is True):
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.base_registry_signaling_sequence = None
        self.base_cache_signaling_sequence = None

        self.cache = LRU(8192)
        # Flag indicating if at least one model cache has been cleared.
        # Useful only in a multi-process context.
        self._any_cache_cleared = False

        with self.cursor() as cr:
            has_unaccent = openerp.modules.db.has_unaccent(cr)
            if config['unaccent'] and not has_unaccent:
                _logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
            self.has_unaccent = config['unaccent'] and has_unaccent

    def cursor(self):
        """ Return a new cursor for the database. The cursor itself may be used
            as a context manager to commit/rollback and close automatically.
        """
        cr = self.test_cr
        if cr is not None:
            # While in test mode, we use one special cursor across requests. The
            # test cursor uses a reentrant lock to serialize accesses. The lock
            # is granted here by cursor(), and automatically released by the
            # cursor itself in its method close().
            cr.acquire()
            return cr
        return self._db.cursor()

    #
    # Mapping abstract methods implementation
    # => mixin provides methods keys, items, values, get, __eq__, and __ne__
    #
    def __len__(self):
        """ Return the size of the registry. """
        return len(self.models)

    def __iter__(self):
        """ Return an iterator over all model names. """
        return iter(self.models)

    def __getitem__(self, model_name):
        """ Return the model with the given name or raise KeyError if it doesn't exist."""
        return self.models[model_name]

    def __call__(self, model_name):
        """ Same as ``self[model_name]``. """
        return self.models[model_name]

    @lazy_property
    def model_cache(self):
        return RegistryManager.model_cache

    @lazy_property
    def pure_function_fields(self):
        """ Return the list of pure function fields (field objects) """
        fields = []
        for mname, fnames in self._pure_function_fields.iteritems():
            model_fields = self[mname]._fields
            for fname in fnames:
                fields.append(model_fields[fname])
        return fields

    @lazy_property
    def field_sequence(self):
        """ Return a function mapping a field to an integer. The value of a
            field is guaranteed to be strictly greater than the value of the
            field's dependencies.
        """
        # map fields on their dependents
        dependents = {
            field: set(dep for dep, _ in model._field_triggers[field] if dep != field)
            for model in self.itervalues()
            for field in model._fields.itervalues()
        }
        # sort them topologically, and associate a sequence number to each field
        mapping = {
            field: num
            for num, field in enumerate(reversed(topological_sort(dependents)))
        }
        return mapping.get

    def clear_manual_fields(self):
        """ Invalidate the cache for manual fields. """
        self._fields_by_model = None

    def get_manual_fields(self, cr, model_name):
        """ Return the manual fields (as a dict) for the given model. """
        if self._fields_by_model is None:
            # Query manual fields for all models at once
            self._fields_by_model = dic = defaultdict(dict)
            cr.execute('SELECT * FROM ir_model_fields WHERE state=%s', ('manual',))
            for field in cr.dictfetchall():
                dic[field['model']][field['name']] = field
        return self._fields_by_model[model_name]

    def do_parent_store(self):
        with self.cursor() as cr:
            for o in self._init_parent:
                self[o]._parent_store_compute(cr)
            self._init = False

    def obj_list(self):
        """ Return the list of model names in this registry."""
        return self.models.keys()

    def add(self, model_name, model):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def load(self, cr, module):
        """ Load a given module in the registry.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instanciates all the classes of a the given module
        and registers them in the registry.

        """
        from .. import models

        loaded_models = OrderedSet()
        def mark_loaded(model):
            # recursively mark model and its children
            loaded_models.add(model._name)
            for child_name in model._inherit_children:
                mark_loaded(self[child_name])

        lazy_property.reset_all(self)

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        for cls in models.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls._build_model(self, cr)
            mark_loaded(model)

        return map(self, loaded_models)

    def setup_models(self, cr, partial=False):
        """ Complete the setup of models.
            This must be called after loading modules and before using the ORM.

            :param partial: ``True`` if all models have not been loaded yet.
        """
        lazy_property.reset_all(self)

        # load custom models
        ir_model = self['ir.model']
        cr.execute('SELECT * FROM ir_model WHERE state=%s', ('manual',))
        for model_data in cr.dictfetchall():
            ir_model._instanciate(cr, SUPERUSER_ID, model_data, {})

        # prepare the setup on all models
        for model in self.models.itervalues():
            model._prepare_setup(cr, SUPERUSER_ID)

        # do the actual setup from a clean state
        self._m2m = {}
        for model in self.models.itervalues():
            model._setup_base(cr, SUPERUSER_ID, partial)

        for model in self.models.itervalues():
            model._setup_fields(cr, SUPERUSER_ID)

        for model in self.models.itervalues():
            model._setup_complete(cr, SUPERUSER_ID)

    def clear_caches(self):
        """ Clear the caches
        This clears the caches associated to methods decorated with
        ``ormcache`` or ``ormcache_multi`` for all the models.
        """
        self.cache.clear()
        for model in self.models.itervalues():
            model.clear_caches()

    # Useful only in a multi-process context.
    def reset_any_cache_cleared(self):
        self._any_cache_cleared = False

    # Useful only in a multi-process context.
    def any_cache_cleared(self):
        return self._any_cache_cleared

    def setup_multi_process_signaling(self):
        if not openerp.multi_process:
            return

        with self.cursor() as cr:
            # Inter-process signaling:
            # The `base_registry_signaling` sequence indicates the whole registry
            # must be reloaded.
            # The `base_cache_signaling sequence` indicates all caches must be
            # invalidated (i.e. cleared).
            cr.execute("""SELECT sequence_name FROM information_schema.sequences WHERE sequence_name='base_registry_signaling'""")
            if not cr.fetchall():
                cr.execute("""CREATE SEQUENCE base_registry_signaling INCREMENT BY 1 START WITH 1""")
                cr.execute("""SELECT nextval('base_registry_signaling')""")
                cr.execute("""CREATE SEQUENCE base_cache_signaling INCREMENT BY 1 START WITH 1""")
                cr.execute("""SELECT nextval('base_cache_signaling')""")

            cr.execute("""
                        SELECT base_registry_signaling.last_value,
                               base_cache_signaling.last_value
                        FROM base_registry_signaling, base_cache_signaling""")
            r, c = cr.fetchone()
            _logger.debug("Multiprocess load registry signaling: [Registry: # %s] "\
                        "[Cache: # %s]",
                        r, c)
            self.base_registry_signaling_sequence = r
            self.base_cache_signaling_sequence = c

    def in_test_mode(self):
        """ Test whether the registry is in 'test' mode. """
        return self.test_cr is not None

    def enter_test_mode(self):
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = self._db.test_cursor()
        RegistryManager.enter_test_mode()

    def leave_test_mode(self):
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.clear_caches()
        self.test_cr.force_close()
        self.test_cr = None
        RegistryManager.leave_test_mode()

    def load_modules(self, force_demo=False, status=None, update_module=False):
        initialize_sys_path()

        force = []
        if force_demo:
            force.append('demo')

        with self.cursor() as cr:
            if not openerp.modules.db.is_initialized(cr):
                _logger.info("init db")
                openerp.modules.db.initialize(cr)
                update_module = True # process auto-installed modules
                config["init"]["all"] = 1
                config['update']['all'] = 1
                if not config['without_demo']:
                    config["demo"]['all'] = 1

            if 'base' in config['update'] or 'all' in config['update']:
                cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

            # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps) 
            graph = openerp.modules.graph.Graph()
            graph.add_module(cr, 'base', force)
            if not graph:
                _logger.critical('module base cannot be loaded! (hint: verify addons-path)')
                raise ImportError('Module `base` cannot be loaded! (hint: verify addons-path)')

            # processed_modules: for cleanup step after install
            # loaded_modules: to avoid double loading
            loaded_modules, processed_modules = self.load_module_graph(
                cr, graph, perform_checks=update_module, report=self._assertion_report)

            load_lang = config.pop('load_language')
            if load_lang or update_module:
                # some base models are used below, so make sure they are set up
                self.setup_models(cr, partial=True)

            if load_lang:
                for lang in load_lang.split(','):
                    self.load_language(cr, lang)

            # STEP 2: Mark other modules to be loaded/updated
            if update_module:
                modobj = self['ir.module.module']
                if ('base' in config['init']) or ('base' in config['update']):
                    _logger.info('updating modules list')
                    modobj.update_list(cr, SUPERUSER_ID)

                self._check_module_names(
                    cr, itertools.chain(config['init'].keys(), config['update'].keys()))

                mods = [k for k in config['init'] if config['init'][k]]
                if mods:
                    ids = modobj.search(cr, SUPERUSER_ID, ['&', ('state', '=', 'uninstalled'), ('name', 'in', mods)])
                    if ids:
                        modobj.button_install(cr, SUPERUSER_ID, ids)

                mods = [k for k in config['update'] if config['update'][k]]
                if mods:
                    ids = modobj.search(cr, SUPERUSER_ID, ['&', ('state', '=', 'installed'), ('name', 'in', mods)])
                    if ids:
                        modobj.button_upgrade(cr, SUPERUSER_ID, ids)

                cr.execute("update ir_module_module set state=%s where name=%s", ('installed', 'base'))
                modobj.invalidate_cache(cr, SUPERUSER_ID, ['state'])


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
                processed_modules += self.load_marked_modules(
                    cr, graph, ['installed', 'to upgrade', 'to remove'],
                    force, self._assertion_report, loaded_modules, update_module)
                if update_module:
                    processed_modules += self.load_marked_modules(
                        cr, graph, ['to install'], force,
                        self._assertion_report, loaded_modules, update_module)

            self.setup_models(cr)

            # STEP 4: Finish and cleanup installations
            if processed_modules:
                cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
                for (model, name) in cr.fetchall():
                    m = self.get(model)
                    if m and not m.is_transient() and not isinstance(m, openerp.models.AbstractModel):
                        _logger.warning('The model %s has no access rules, consider adding one. E.g. access_%s,access_%s,model_%s,,1,0,0,0',
                                        model, model.replace('.', '_'), model.replace('.', '_'), model.replace('.', '_'))

                # Temporary warning while we remove access rights on osv_memory objects, as they have
                # been replaced by owner-only access rights
                cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
                for (model, name) in cr.fetchall():
                    if model in self and self[model].is_transient():
                        _logger.warning('The transient model %s (%s) should not have explicit access rules!', model, name)

                cr.execute("SELECT model from ir_model")
                for (model,) in cr.fetchall():
                    if model in self:
                        self[model]._check_removed_columns(cr, log=True)
                    else:
                        _logger.warning("Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)", model)

                # Cleanup orphan records
                self['ir.model.data']._process_end(cr, SUPERUSER_ID, processed_modules)

            for kind in ('init', 'demo', 'update'):
                config[kind] = {}

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
                            py_module = sys.modules['openerp.addons.%s' % (pkg.name,)]
                            getattr(py_module, uninstall_hook)(cr, self)

                    self['ir.module.module'].module_uninstall(cr, SUPERUSER_ID, modules_to_remove.values())
                    # Recursive reload, should only happen once, because there should be no
                    # modules to remove next time
                    cr.commit()
                    _logger.info('Reloading registry once more after uninstalling modules')
                    openerp.api.Environment.reset()
                    return RegistryManager.new(
                        cr.dbname, force_demo=force_demo, update_module=update_module)

            # STEP 6: verify custom views on every model
            if update_module:
                Views = self['ir.ui.view']
                custom_view_test = True
                for model in self.models:
                    if not Views._validate_custom_views(cr, SUPERUSER_ID, model):
                        custom_view_test = False
                        _logger.error('invalid custom view(s) for model %s',
                                      model)
                self._assertion_report.record_result(custom_view_test)

            if self._assertion_report.failures:
                _logger.error(
                    'At least one test failed when loading the modules.')
            else:
                _logger.info('Modules loaded.')

            # STEP 7: call _register_hook on every model
            for model in self.models.values():
                model._register_hook(cr)

        with closing(self.cursor()) as cr:
            # STEP 8: Run the post-install tests
            t0 = time.time()
            t0_sql = openerp.sql_db.sql_counter
            if config['test_enable']:
                cr.execute(
                    "SELECT name FROM ir_module_module WHERE state='installed'")
                for module_name in cr.fetchall():
                    self._assertion_report.record_result(run_unit_tests(module_name[0], cr.dbname, position=runs_post_install))
                _logger.log(25, "All post-tested in %.2fs, %s queries", time.time() - t0, openerp.sql_db.sql_counter - t0_sql)

    def load_marked_modules(self, cr, graph, states, force, report, loaded_modules, perform_checks):
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
            loaded, processed = self.load_module_graph(cr, graph, report=report, skip_modules=loaded_modules, perform_checks=perform_checks)
            processed_modules.extend(processed)
            loaded_modules.extend(loaded)
            if not processed:
                break
        return processed_modules


    def load_module_graph(self, cr, graph, perform_checks=True, skip_modules=None, report=None):
        """Migrates+Updates or Installs all module nodes from ``graph``
           :param graph: graph of module nodes to load
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
                cr.rollback()
                # avoid keeping stale xml_id, etc. in cache
                self.clear_caches()


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
                    convert_file(cr, module_name, filename, idref, mode, noupdate, kind, report)
            finally:
                if kind in ('demo', 'test'):
                    threading.currentThread().testing = False

        processed_modules = []
        loaded_modules = []
        migrations = migration.MigrationManager(cr, graph)
        _logger.info('loading %d modules...', len(graph))

        self.clear_manual_fields()

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

            new_install = package.state == 'to install'
            py_module = None
            if new_install:
                py_module = sys.modules['openerp.addons.%s' % (module_name,)]
                pre_init = package.info.get('pre_init_hook')
                if pre_init:
                    getattr(py_module, pre_init)(cr)

            models = self.load(cr, package)

            loaded_modules.append(package.name)
            if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
                self.setup_models(cr, partial=True)
                init_models(models, cr, {'module': package.name})

            idref = {}

            mode = 'update'
            if hasattr(package, 'init') or package.state == 'to install':
                mode = 'init'

            if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
                # Can't put this line out of the loop: ir.module.module will be
                # registered by init_models() above.
                modobj = self['ir.module.module'].browse(cr, SUPERUSER_ID, module_id, {
                    'overwrite': config["overwrite_existing_translations"]
                })

                if perform_checks:
                    modobj.check()

                if package.state=='to upgrade':
                    # upgrading the module information
                    modobj.write(modobj.get_values_from_terp(package.data))

                _load_data(cr, module_name, idref, mode, kind='data')
                has_demo = hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed')
                if has_demo:
                    _load_data(cr, module_name, idref, mode, kind='demo')
                    cr.execute('update ir_module_module set demo=%s where id=%s', (True, module_id))
                    modobj.invalidate_cache(['demo'], [module_id])

                migrations.migrate_module(package, 'post')

                # Update translations for all installed languages
                modobj.update_translations(None)

                self._init_modules.add(package.name)

                if new_install:
                    post_init = package.info.get('post_init_hook')
                    if post_init:
                        getattr(py_module, post_init)(cr, self)

                # validate all the views at a whole
                self['ir.ui.view']._validate_module_views(
                    cr, SUPERUSER_ID, module_name)

                if has_demo:
                    # launch tests only in demo mode, allowing tests to use demo data.
                    if config.options['test_enable']:
                        # Yamel test
                        report.record_result(load_test(module_name, idref, mode))
                        # Python tests
                        ir_http = self['ir.http']
                        if hasattr(ir_http, '_routing_map'):
                            # Force routing map to be rebuilt between each module test suite
                            del ir_http._routing_map
                        report.record_result(run_unit_tests(module_name, cr.dbname))

                processed_modules.append(package.name)

                ver = adapt_version(package.data['version'])
                # Set new modules and dependencies
                modobj.write({'state': 'installed', 'latest_version': ver})

                package.state = 'installed'
                for kind in ('init', 'demo', 'update'):
                    if hasattr(package, kind):
                        delattr(package, kind)

            self._init_modules.add(package.name)
            cr.commit()

        _logger.log(25, "%s modules loaded in %.2fs, %s queries", len(graph), time.time() - t0, openerp.sql_db.sql_counter - t0_sql)

        self.clear_manual_fields()

        cr.commit()

        return loaded_modules, processed_modules

    def _check_module_names(self, cr, module_names):
        mod_names = set(module_names)
        # ignore dummy 'all' module
        if 'base' in mod_names and 'all' in mod_names:
            mod_names.remove('all')

        if mod_names:
            cr.execute("SELECT count(id) AS count FROM ir_module_module WHERE name in %s", (tuple(mod_names),))
            if cr.dictfetchone()['count'] != len(mod_names):
                # find out what module name(s) are incorrect:
                cr.execute("SELECT name FROM ir_module_module")
                incorrect_names = mod_names.difference([x['name'] for x in cr.dictfetchall()])
                _logger.warning('invalid module names, ignored: %s', ", ".join(incorrect_names))

    def load_language(self, cr, lang):
        """Loads a translation terms for a language.

        Used mainly to automate language loading at db initialization.

        :param str lang: language ISO code with optional _underscore_ and l10n
                         flavor (ex: 'fr', 'fr_BE', but not 'fr-BE')
        """
        language_installer = self['base.language.install']
        oid = language_installer.create(cr, SUPERUSER_ID, {'lang': lang})
        language_installer.lang_install(cr, SUPERUSER_ID, [oid])


class DummyRLock(object):
    """ Dummy reentrant lock, to be used while running rpc and js tests """
    def acquire(self):
        pass
    def release(self):
        pass
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release()

class RegistryManager(object):
    """ Model registries manager.

        The manager is responsible for creation and deletion of model
        registries (essentially database connection/model registry pairs).

    """
    _registries = None
    _model_cache = None
    _lock = threading.RLock()
    _saved_lock = None

    @classproperty
    def registries(cls):
        if cls._registries is None:
            size = config.get('registry_lru_size', None)
            if not size:
                # Size the LRU depending of the memory limits
                if os.name != 'posix':
                    # cannot specify the memory limit soft on windows...
                    size = 42
                else:
                    # A registry takes 10MB of memory on average, so we reserve
                    # 10Mb (registry) + 5Mb (working memory) per registry
                    avgsz = 15 * 1024 * 1024
                    size = int(config['limit_memory_soft'] / avgsz)

            cls._registries = LRU(size)
        return cls._registries

    @classproperty
    def model_cache(cls):
        """ A cache for model classes, indexed by their base classes. """
        if cls._model_cache is None:
            # we cache 256 classes per registry on average
            cls._model_cache = LRU(cls.registries.count * 256)
        return cls._model_cache

    @classmethod
    def lock(cls):
        """ Return the current registry lock. """
        return cls._lock

    @classmethod
    def enter_test_mode(cls):
        """ Enter the 'test' mode, where the registry is no longer locked. """
        assert cls._saved_lock is None
        cls._lock, cls._saved_lock = DummyRLock(), cls._lock

    @classmethod
    def leave_test_mode(cls):
        """ Leave the 'test' mode. """
        assert cls._saved_lock is not None
        cls._lock, cls._saved_lock = cls._saved_lock, None

    @classmethod
    def get(cls, db_name, force_demo=False, status=None, update_module=False):
        """ Return a registry for a given database name."""
        with cls.lock():
            try:
                return cls.registries[db_name]
            except KeyError:
                return cls.new(db_name, force_demo, status,
                               update_module)
            finally:
                # set db tracker - cleaned up at the WSGI
                # dispatching phase in openerp.service.wsgi_server.application
                threading.current_thread().dbname = db_name

    @classmethod
    def new(cls, db_name, force_demo=False, status=None,
            update_module=False):
        """ Create and return a new registry for a given database name.

        The (possibly) previous registry for that database name is discarded.

        """
        import openerp.modules
        with cls.lock(), openerp.api.Environment.manage():
            # remove existing registry if any
            cls.delete(db_name)

            # Initializing a registry will call general code which will in
            # turn call registries.get (this object) to obtain the registry
            # being initialized. Make it available in the registries
            # dictionary then remove it if an exception is raised.
            registry = cls.registries[db_name] = Registry(db_name)
            try:
                registry.setup_multi_process_signaling()
                registry.load_modules(force_demo, status, update_module)
            except Exception:
                del cls.registries[db_name]
                raise

            # load_modules() above can replace the registry by calling
            # indirectly new() again (when modules have to be uninstalled).
            # Yeah, crazy.
            registry = cls.registries[db_name]

            registry.do_parent_store()

        registry.ready = True

        if update_module:
            # only in case of update, otherwise we'll have an infinite reload loop!
            cls.signal_registry_change(db_name)
        return registry

    @classmethod
    def delete(cls, db_name):
        """Delete the registry linked to a given database.  """
        with cls.lock():
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()
                del cls.registries[db_name]

    @classmethod
    def delete_all(cls):
        """Delete all the registries. """
        with cls.lock():
            for db_name in cls.registries.keys():
                cls.delete(db_name)

    @classmethod
    def clear_caches(cls, db_name):
        """Clear caches

        This clears the caches associated to methods decorated with
        ``ormcache`` or ``ormcache_multi`` for all the models
        of the given database name.

        This method is given to spare you a ``RegistryManager.get(db_name)``
        that would loads the given database if it was not already loaded.
        """
        with cls.lock():
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()

    @classmethod
    def check_registry_signaling(cls, db_name):
        """
        Check if the modules have changed and performs all necessary operations to update
        the registry of the corresponding database.


        :returns: True if changes has been detected in the database and False otherwise.
        """
        changed = False
        if openerp.multi_process and db_name in cls.registries:
            registry = cls.get(db_name)
            with closing(registry.cursor()) as cr:
                cr.execute("""
                    SELECT base_registry_signaling.last_value,
                           base_cache_signaling.last_value
                    FROM base_registry_signaling, base_cache_signaling""")
                r, c = cr.fetchone()
                _logger.debug("Multiprocess signaling check: [Registry - old# %s new# %s] "\
                    "[Cache - old# %s new# %s]",
                    registry.base_registry_signaling_sequence, r,
                    registry.base_cache_signaling_sequence, c)
                # Check if the model registry must be reloaded (e.g. after the
                # database has been updated by another process).
                if registry.base_registry_signaling_sequence is not None and registry.base_registry_signaling_sequence != r:
                    changed = True
                    _logger.info("Reloading the model registry after database signaling.")
                    registry = cls.new(db_name)
                # Check if the model caches must be invalidated (e.g. after a write
                # occured on another process). Don't clear right after a registry
                # has been reload.
                elif registry.base_cache_signaling_sequence is not None and registry.base_cache_signaling_sequence != c:
                    changed = True
                    _logger.info("Invalidating all model caches after database signaling.")
                    registry.clear_caches()
                    registry.reset_any_cache_cleared()
                registry.base_registry_signaling_sequence = r
                registry.base_cache_signaling_sequence = c
        return changed

    @classmethod
    def signal_caches_change(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            # Check the registries if any cache has been cleared and signal it
            # through the database to other processes.
            registry = cls.get(db_name)
            if registry.any_cache_cleared():
                _logger.info("At least one model cache has been cleared, signaling through the database.")
                with closing(registry.cursor()) as cr:
                    cr.execute("select nextval('base_cache_signaling')")
                    r = cr.fetchone()[0]
                registry.base_cache_signaling_sequence = r
                registry.reset_any_cache_cleared()

    @classmethod
    def signal_registry_change(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            _logger.info("Registry changed, signaling through the database")
            registry = cls.get(db_name)
            # cursor-as-context-manager will commit the cursor implicitly,
            # here we don't want or need to pay for a commit. Closing will
            # just call close() and rollback the txn
            with closing(registry.cursor()) as cr:
                cr.execute("select nextval('base_registry_signaling')")
                r = cr.fetchone()[0]
            registry.base_registry_signaling_sequence = r
