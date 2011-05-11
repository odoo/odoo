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

import os, sys, imp
from os.path import join as opj
import itertools
import zipimport

import openerp

import openerp.osv as osv
import openerp.tools as tools
import openerp.tools.osutil as osutil
from openerp.tools.safe_eval import safe_eval as eval
import openerp.pooler as pooler
from openerp.tools.translate import _

import openerp.netsvc as netsvc

import zipfile
import openerp.release as release

import re
import base64
from zipfile import PyZipFile, ZIP_DEFLATED
from cStringIO import StringIO

import logging

import openerp.modules.db
import openerp.modules.graph

logger = netsvc.Logger()

_ad = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addons') # default addons path (base)
ad_paths = []

# Modules already loaded
loaded = []

def initialize_sys_path():
    global ad_paths

    if ad_paths:
        return

    ad_paths = map(lambda m: os.path.abspath(tools.ustr(m.strip())), tools.config['addons_path'].split(','))

    sys.path.insert(1, _ad)

    ad_cnt=1
    for adp in ad_paths:
        if adp != _ad:
            sys.path.insert(ad_cnt, adp)
            ad_cnt+=1

    ad_paths.append(_ad)    # for get_module_path

def open_openerp_namespace():
    # See comment for open_openerp_namespace.
    if openerp.conf.deprecation.open_openerp_namespace:
        for k, v in list(sys.modules.items()):
            if k.startswith('openerp.') and sys.modules.get(k[8:]) is None:
                sys.modules[k[8:]] = v


def get_module_path(module, downloaded=False):
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    initialize_sys_path()
    for adp in ad_paths:
        if os.path.exists(opj(adp, module)) or os.path.exists(opj(adp, '%s.zip' % module)):
            return opj(adp, module)

    if downloaded:
        return opj(_ad, module)
    logger.notifyChannel('init', netsvc.LOG_WARNING, 'module %s: module not found' % (module,))
    return False


def get_module_filetree(module, dir='.'):
    path = get_module_path(module)
    if not path:
        return False

    dir = os.path.normpath(dir)
    if dir == '.':
        dir = ''
    if dir.startswith('..') or (dir and dir[0] == '/'):
        raise Exception('Cannot access file outside the module')

    if not os.path.isdir(path):
        # zipmodule
        zip = zipfile.ZipFile(path + ".zip")
        files = ['/'.join(f.split('/')[1:]) for f in zip.namelist()]
    else:
        files = osutil.listdir(path, True)

    tree = {}
    for f in files:
        if not f.startswith(dir):
            continue

        if dir:
            f = f[len(dir)+int(not dir.endswith('/')):]
        lst = f.split(os.sep)
        current = tree
        while len(lst) != 1:
            current = current.setdefault(lst.pop(0), {})
        current[lst.pop(0)] = None

    return tree

def zip_directory(directory, b64enc=True, src=True):
    """Compress a directory

    @param directory: The directory to compress
    @param base64enc: if True the function will encode the zip file with base64
    @param src: Integrate the source files

    @return: a string containing the zip file
    """

    RE_exclude = re.compile('(?:^\..+\.swp$)|(?:\.py[oc]$)|(?:\.bak$)|(?:\.~.~$)', re.I)

    def _zippy(archive, path, src=True):
        path = os.path.abspath(path)
        base = os.path.basename(path)
        for f in osutil.listdir(path, True):
            bf = os.path.basename(f)
            if not RE_exclude.search(bf) and (src or bf in ('__openerp__.py', '__terp__.py') or not bf.endswith('.py')):
                archive.write(os.path.join(path, f), os.path.join(base, f))

    archname = StringIO()
    archive = PyZipFile(archname, "w", ZIP_DEFLATED)

    # for Python 2.5, ZipFile.write() still expects 8-bit strings (2.6 converts to utf-8)
    directory = tools.ustr(directory).encode('utf-8')

    archive.writepy(directory)
    _zippy(archive, directory, src=src)
    archive.close()
    archive_data = archname.getvalue()
    archname.close()

    if b64enc:
        return base64.encodestring(archive_data)

    return archive_data

def get_module_as_zip(modulename, b64enc=True, src=True):
    """Generate a module as zip file with the source or not and can do a base64 encoding

    @param modulename: The module name
    @param b64enc: if True the function will encode the zip file with base64
    @param src: Integrate the source files

    @return: a stream to store in a file-like object
    """

    ap = get_module_path(str(modulename))
    if not ap:
        raise Exception('Unable to find path for module %s' % modulename)

    ap = ap.encode('utf8')
    if os.path.isfile(ap + '.zip'):
        val = file(ap + '.zip', 'rb').read()
        if b64enc:
            val = base64.encodestring(val)
    else:
        val = zip_directory(ap, b64enc, src)

    return val


def get_module_resource(module, *args):
    """Return the full path of a resource of the given module.

    @param module: the module
    @param args: the resource path components

    @return: absolute path to the resource

    TODO name it get_resource_path
    TODO make it available inside on osv object (self.get_resource_path)
    """
    a = get_module_path(module)
    if not a: return False
    resource_path = opj(a, *args)
    if zipfile.is_zipfile( a +'.zip') :
        zip = zipfile.ZipFile( a + ".zip")
        files = ['/'.join(f.split('/')[1:]) for f in zip.namelist()]
        resource_path = '/'.join(args)
        if resource_path in files:
            return opj(a, resource_path)
    elif os.path.exists(resource_path):
        return resource_path
    return False

def get_modules():
    """Returns the list of module names
    """
    def listdir(dir):
        def clean(name):
            name = os.path.basename(name)
            if name[-4:] == '.zip':
                name = name[:-4]
            return name

        def is_really_module(name):
            name = opj(dir, name)
            return os.path.isdir(name) or zipfile.is_zipfile(name)
        return map(clean, filter(is_really_module, os.listdir(dir)))

    plist = []
    initialize_sys_path()
    for ad in ad_paths:
        plist.extend(listdir(ad))
    return list(set(plist))

def load_information_from_description_file(module):
    """
    :param module: The name of the module (sale, purchase, ...)
    """

    terp_file = get_module_resource(module, '__openerp__.py')
    if not terp_file:
        terp_file = get_module_resource(module, '__terp__.py')
    mod_path = get_module_path(module)
    if terp_file:
        info = {}
        if os.path.isfile(terp_file) or zipfile.is_zipfile(mod_path+'.zip'):
            terp_f = tools.file_open(terp_file)
            try:
                info = eval(terp_f.read())
            except Exception:
                logger.notifyChannel('modules', netsvc.LOG_ERROR,
                    'module %s: exception while evaluating file %s' %
                    (module, terp_file))
                raise
            finally:
                terp_f.close()
            # TODO the version should probably be mandatory
            info.setdefault('version', '0')
            info.setdefault('category', 'Uncategorized')
            info.setdefault('depends', [])
            info.setdefault('author', '')
            info.setdefault('website', '')
            info.setdefault('name', False)
            info.setdefault('description', '')
            info['certificate'] = info.get('certificate') or None
            info['web'] = info.get('web') or False
            info['license'] = info.get('license') or 'AGPL-3'
            info.setdefault('installable', True)
            info.setdefault('active', False)
            for kind in ['data', 'demo', 'test',
                'init_xml', 'update_xml', 'demo_xml']:
                info.setdefault(kind, [])
            return info

    #TODO: refactor the logger in this file to follow the logging guidelines
    #      for 6.0
    logging.getLogger('modules').debug('module %s: no descriptor file'
        ' found: __openerp__.py or __terp__.py (deprecated)', module)
    return {}


def get_modules_with_version():
    modules = get_modules()
    res = {}
    for module in modules:
        try:
            info = load_information_from_description_file(module)
            res[module] = "%s.%s" % (release.major_version, info['version'])
        except Exception, e:
            continue
    return res


def init_module_models(cr, module_name, obj_list):
    """ Initialize a list of models.

    Call _auto_init and init on each model to create or update the
    database tables supporting the models.

    TODO better explanation of _auto_init and init.

    """

    logger.notifyChannel('init', netsvc.LOG_INFO,
        'module %s: creating or updating database tables' % module_name)
    # TODO _auto_init doesn't seem to return anything
    # so this todo list would be useless.
    todo = []
    for obj in obj_list:
        try:
            # TODO the module in the context doesn't seem usefull:
            # it is available (at least) in the class' _module attribute.
            # (So module_name would be useless too.)
            result = obj._auto_init(cr, {'module': module_name})
        except Exception, e:
            raise
        if result:
            todo += result
        if hasattr(obj, 'init'):
            obj.init(cr)
        cr.commit()
    todo.sort()
    for t in todo:
        t[1](cr, *t[2])
    cr.commit()


def load_module(module_name):
    """ Load a Python module found on the addons paths."""
    fm = imp.find_module(module_name, ad_paths)
    try:
        imp.load_module(module_name, *fm)
    finally:
        if fm[0]:
            fm[0].close()


def register_module_classes(m):
    """ Register module named m, if not already registered.

    This will load the module and register all of its models. (Actually, the
    explicit constructor call of each of the models inside the module will
    register them.)

    """

    def log(e):
        mt = isinstance(e, zipimport.ZipImportError) and 'zip ' or ''
        msg = "Couldn't load %smodule %s" % (mt, m)
        logger.notifyChannel('init', netsvc.LOG_CRITICAL, msg)
        logger.notifyChannel('init', netsvc.LOG_CRITICAL, e)

    global loaded
    if m in loaded:
        return
    logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: registering objects' % m)
    mod_path = get_module_path(m)

    initialize_sys_path()
    try:
        zip_mod_path = mod_path + '.zip'
        if not os.path.isfile(zip_mod_path):
            load_module(m)
        else:
            zimp = zipimport.zipimporter(zip_mod_path)
            zimp.load_module(m)
    except Exception, e:
        log(e)
        raise
    else:
        loaded.append(m)


class MigrationManager(object):
    """
        This class manage the migration of modules
        Migrations files must be python files containing a "migrate(cr, installed_version)" function.
        Theses files must respect a directory tree structure: A 'migrations' folder which containt a
        folder by version. Version can be 'module' version or 'server.module' version (in this case,
        the files will only be processed by this version of the server). Python file names must start
        by 'pre' or 'post' and will be executed, respectively, before and after the module initialisation
        Example:

            <moduledir>
            `-- migrations
                |-- 1.0
                |   |-- pre-update_table_x.py
                |   |-- pre-update_table_y.py
                |   |-- post-clean-data.py
                |   `-- README.txt              # not processed
                |-- 5.0.1.1                     # files in this folder will be executed only on a 5.0 server
                |   |-- pre-delete_table_z.py
                |   `-- post-clean-data.py
                `-- foo.py                      # not processed

        This similar structure is generated by the maintenance module with the migrations files get by
        the maintenance contract

    """
    def __init__(self, cr, graph):
        self.cr = cr
        self.graph = graph
        self.migrations = {}
        self._get_files()

    def _get_files(self):

        """
        import addons.base.maintenance.utils as maintenance_utils
        maintenance_utils.update_migrations_files(self.cr)
        #"""

        for pkg in self.graph:
            self.migrations[pkg.name] = {}
            if not (hasattr(pkg, 'update') or pkg.state == 'to upgrade'):
                continue

            self.migrations[pkg.name]['module'] = get_module_filetree(pkg.name, 'migrations') or {}
            self.migrations[pkg.name]['maintenance'] = get_module_filetree('base', 'maintenance/migrations/' + pkg.name) or {}

    def migrate_module(self, pkg, stage):
        assert stage in ('pre', 'post')
        stageformat = {'pre': '[>%s]',
                       'post': '[%s>]',
                      }

        if not (hasattr(pkg, 'update') or pkg.state == 'to upgrade'):
            return

        def convert_version(version):
            if version.startswith(release.major_version) and version != release.major_version:
                return version  # the version number already containt the server version
            return "%s.%s" % (release.major_version, version)

        def _get_migration_versions(pkg):
            def __get_dir(tree):
                return [d for d in tree if tree[d] is not None]

            versions = list(set(
                __get_dir(self.migrations[pkg.name]['module']) +
                __get_dir(self.migrations[pkg.name]['maintenance'])
            ))
            versions.sort(key=lambda k: parse_version(convert_version(k)))
            return versions

        def _get_migration_files(pkg, version, stage):
            """ return a list of tuple (module, file)
            """
            m = self.migrations[pkg.name]
            lst = []

            mapping = {'module': opj(pkg.name, 'migrations'),
                       'maintenance': opj('base', 'maintenance', 'migrations', pkg.name),
                      }

            for x in mapping.keys():
                if version in m[x]:
                    for f in m[x][version]:
                        if m[x][version][f] is not None:
                            continue
                        if not f.startswith(stage + '-'):
                            continue
                        lst.append(opj(mapping[x], version, f))
            lst.sort()
            return lst

        def mergedict(a, b):
            a = a.copy()
            a.update(b)
            return a

        from openerp.tools.parse_version import parse_version

        parsed_installed_version = parse_version(pkg.installed_version or '')
        current_version = parse_version(convert_version(pkg.data['version']))

        versions = _get_migration_versions(pkg)

        for version in versions:
            if parsed_installed_version < parse_version(convert_version(version)) <= current_version:

                strfmt = {'addon': pkg.name,
                          'stage': stage,
                          'version': stageformat[stage] % version,
                          }

                for pyfile in _get_migration_files(pkg, version, stage):
                    name, ext = os.path.splitext(os.path.basename(pyfile))
                    if ext.lower() != '.py':
                        continue
                    mod = fp = fp2 = None
                    try:
                        fp = tools.file_open(pyfile)

                        # imp.load_source need a real file object, so we create
                        # one from the file-like object we get from file_open
                        fp2 = os.tmpfile()
                        fp2.write(fp.read())
                        fp2.seek(0)
                        try:
                            mod = imp.load_source(name, pyfile, fp2)
                            logger.notifyChannel('migration', netsvc.LOG_INFO, 'module %(addon)s: Running migration %(version)s %(name)s' % mergedict({'name': mod.__name__}, strfmt))
                            mod.migrate(self.cr, pkg.installed_version)
                        except ImportError:
                            logger.notifyChannel('migration', netsvc.LOG_ERROR, 'module %(addon)s: Unable to load %(stage)s-migration file %(file)s' % mergedict({'file': pyfile}, strfmt))
                            raise
                        except AttributeError:
                            logger.notifyChannel('migration', netsvc.LOG_ERROR, 'module %(addon)s: Each %(stage)s-migration file must have a "migrate(cr, installed_version)" function' % strfmt)
                        except:
                            raise
                    finally:
                        if fp:
                            fp.close()
                        if fp2:
                            fp2.close()
                        if mod:
                            del mod


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

    def load_init_xml(cr, m, idref, mode):
        _load_data(cr, m, idref, mode, 'init_xml')

    def load_update_xml(cr, m, idref, mode):
        _load_data(cr, m, idref, mode, 'update_xml')

    def load_demo_xml(cr, m, idref, mode):
        _load_data(cr, m, idref, mode, 'demo_xml')

    def load_data(cr, module_name, idref, mode):
        _load_data(cr, module_name, idref, mode, 'data')

    def load_demo(cr, module_name, idref, mode):
        _load_data(cr, module_name, idref, mode, 'demo')

    def load_test(cr, module_name, idref, mode):
        cr.commit()
        if not tools.config.options['test_disable']:
            try:
                _load_data(cr, module_name, idref, mode, 'test')
            except Exception, e:
                logging.getLogger('test').exception('Tests failed to execute in module %s', module_name)
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
            log = logging.getLogger('init')
            log.info("module %s: loading %s", module_name, filename)
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
    statusi = 0
    pool = pooler.get_pool(cr.dbname)
    migrations = MigrationManager(cr, graph)
    logger.notifyChannel('init', netsvc.LOG_DEBUG, 'loading %d packages..' % len(graph))

    # register, instanciate and initialize models for each modules
    for package in graph:
        if skip_modules and package.name in skip_modules:
            continue
        logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: loading objects' % package.name)
        migrations.migrate_module(package, 'pre')
        register_module_classes(package.name)
        models = pool.instanciate(package.name, cr)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_models(cr, package.name, models)
        cr.commit()

    # load data for each modules
    modobj = pool.get('ir.module.module')
    for package in graph:
        status['progress'] = (float(statusi)+0.1) / len(graph)
        m = package.name
        mid = package.id

        if skip_modules and m in skip_modules:
            continue

        if perform_checks:
            modobj.check(cr, 1, [mid])

        idref = {}
        status['progress'] = (float(statusi)+0.4) / len(graph)

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            if package.state=='to upgrade':
                # upgrading the module information
                modobj.write(cr, 1, [mid], modobj.get_values_from_terp(package.data))
            load_init_xml(cr, m, idref, mode)
            load_update_xml(cr, m, idref, mode)
            load_data(cr, m, idref, mode)
            if hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed'):
                status['progress'] = (float(statusi)+0.75) / len(graph)
                load_demo_xml(cr, m, idref, mode)
                load_demo(cr, m, idref, mode)
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, mid))

                # launch tests only in demo mode, as most tests will depend
                # on demo data. Other tests can be added into the regular
                # 'data' section, but should probably not alter the data,
                # as there is no rollback.
                load_test(cr, m, idref, mode)

            processed_modules.append(package.name)

            migrations.migrate_module(package, 'post')

            ver = release.major_version + '.' + package.data['version']
            # Set new modules and dependencies
            modobj.write(cr, 1, [mid], {'state': 'installed', 'latest_version': ver})
            cr.commit()
            # Update translations for all installed languages
            modobj.update_translations(cr, 1, [mid], None)
            cr.commit()

            package.state = 'installed'
            for kind in ('init', 'demo', 'update'):
                if hasattr(package, kind):
                    delattr(package, kind)

        statusi += 1

    cr.commit()

    return processed_modules

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

def load_modules(db, force_demo=False, status=None, update_module=False):
    # TODO status['progress'] reporting is broken: used twice (and reset each
    # time to zero) in load_module_graph, not fine-grained enough.
    # It should be a method exposed by the pool.

    initialize_sys_path()

    open_openerp_namespace()

    cr = db.cursor()
    if cr:
        cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname='ir_module_module'")
        if len(cr.fetchall())==0:
            logger.notifyChannel("init", netsvc.LOG_INFO, "init db")
            openerp.modules.db.initialize(cr)
            tools.config["init"]["all"] = 1
            tools.config['update']['all'] = 1
            if not tools.config['without_demo']:
                tools.config["demo"]['all'] = 1
    force = []
    if force_demo:
        force.append('demo')

    # This is a brand new pool, just created in pooler.get_db_and_pool()
    pool = pooler.get_pool(cr.dbname)

    try:
        processed_modules = []
        report = tools.assertion_report()
        # NOTE: Try to also load the modules that have been marked as uninstallable previously...
        STATES_TO_LOAD = ['installed', 'to upgrade', 'uninstallable']
        if 'base' in tools.config['update'] or 'all' in tools.config['update']:
            cr.execute("update ir_module_module set state=%s where name=%s and state=%s", ('to upgrade', 'base', 'installed'))

        # STEP 1: LOAD BASE (must be done before module dependencies can be computed for later steps) 
        graph = openerp.modules.graph.Graph()
        graph.add_module(cr, 'base', force)
        if not graph:
            logger.notifyChannel('init', netsvc.LOG_CRITICAL, 'module base cannot be loaded! (hint: verify addons-path)')
            raise osv.osv.except_osv(_('Could not load base module'), _('module base cannot be loaded! (hint: verify addons-path)'))
        processed_modules.extend(load_module_graph(cr, graph, status, perform_checks=(not update_module), report=report))

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

            STATES_TO_LOAD += ['to install']


        # STEP 3: Load marked modules (skipping base which was done in STEP 1)
        loop_guardrail = 0
        while True:
            loop_guardrail += 1
            if loop_guardrail > 100:
                raise ValueError('Possible recursive module tree detected, aborting.')
            cr.execute("SELECT name from ir_module_module WHERE state IN %s" ,(tuple(STATES_TO_LOAD),))

            module_list = [name for (name,) in cr.fetchall() if name not in graph]
            if not module_list:
                break

            new_modules_in_graph = graph.add_modules(cr, module_list, force)
            if new_modules_in_graph == 0:
                # nothing to load
                break

            logger.notifyChannel('init', netsvc.LOG_DEBUG, 'Updating graph with %d more modules' % (len(module_list)))
            processed_modules.extend(load_module_graph(cr, graph, status, report=report, skip_modules=processed_modules))

        # load custom models
        cr.execute('select model from ir_model where state=%s', ('manual',))
        for model in cr.dictfetchall():
            pool.get('ir.model').instanciate(cr, 1, model['model'], {})

        # STEP 4: Finish and cleanup
        if processed_modules:
            cr.execute("""select model,name from ir_model where id NOT IN (select distinct model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if model_obj and not isinstance(model_obj, osv.osv.osv_memory):
                    logger.notifyChannel('init', netsvc.LOG_WARNING, 'object %s (%s) has no access rules!' % (model, name))

            # Temporary warning while we remove access rights on osv_memory objects, as they have
            # been replaced by owner-only access rights
            cr.execute("""select distinct mod.model, mod.name from ir_model_access acc, ir_model mod where acc.model_id = mod.id""")
            for (model, name) in cr.fetchall():
                model_obj = pool.get(model)
                if isinstance(model_obj, osv.osv.osv_memory):
                    logger.notifyChannel('init', netsvc.LOG_WARNING, 'In-memory object %s (%s) should not have explicit access rules!' % (model, name))

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                obj = pool.get(model)
                if obj:
                    obj._check_removed_columns(cr, log=True)
                else:
                    logger.notifyChannel('init', netsvc.LOG_WARNING, "Model %s is referenced but not present in the orm pool!" % model)

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
