# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os, sys, imp
from os.path import join as opj
import itertools
import zipimport

import osv
import tools
import tools.osutil
import pooler


import netsvc
from osv import fields

import zipfile
import release

import re
import base64
from zipfile import PyZipFile, ZIP_DEFLATED
from cStringIO import StringIO


logger = netsvc.Logger()

_ad = os.path.abspath(opj(tools.config['root_path'], 'addons'))     # default addons path (base)
ad = os.path.abspath(tools.config['addons_path'])           # alternate addons path

sys.path.insert(1, _ad)
if ad != _ad:
    sys.path.insert(1, ad)

# Modules already loaded
loaded = []


class Graph(dict):

    def addNode(self, name, deps):
        max_depth, father = 0, None
        for n in [Node(x, self) for x in deps]:
            if n.depth >= max_depth:
                father = n
                max_depth = n.depth
        if father:
            father.addChild(name)
        else:
            Node(name, self)

    def update_from_db(self, cr):
        # update the graph with values from the database (if exist)
        ## First, we set the default values for each package in graph
        additional_data = dict.fromkeys(self.keys(), {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None})
        ## Then we get the values from the database
        cr.execute('SELECT name, id, state, demo AS dbdemo, latest_version AS installed_version'
                   '  FROM ir_module_module'
                   ' WHERE name in %s',
                    (tuple(additional_data),)
                   )

        ## and we update the default values with values from the database
        additional_data.update(dict([(x.pop('name'), x) for x in cr.dictfetchall()]))
        
        for package in self.values():
            for k, v in additional_data[package.name].items():
                setattr(package, k, v)



    def __iter__(self):
        level = 0
        done = set(self.keys())
        while done:
            level_modules = [(name, module) for name, module in self.items() if module.depth==level]
            for name, module in level_modules:
                done.remove(name)
                yield module
            level += 1

class Singleton(object):
    def __new__(cls, name, graph):
        if name in graph:
            inst = graph[name]
        else:
            inst = object.__new__(cls)
            inst.name = name
            graph[name] = inst
        return inst


class Node(Singleton):

    def __init__(self, name, graph):
        self.graph = graph
        if not hasattr(self, 'children'):
            self.children = []
        if not hasattr(self, 'depth'):
            self.depth = 0

    def addChild(self, name):
        node = Node(name, self.graph)
        node.depth = self.depth + 1
        if node not in self.children:
            self.children.append(node)
        for attr in ('init', 'update', 'demo'):
            if hasattr(self, attr):
                setattr(node, attr, True)
        self.children.sort(lambda x, y: cmp(x.name, y.name))

    def __setattr__(self, name, value):
        super(Singleton, self).__setattr__(name, value)
        if name in ('init', 'update', 'demo'):
            tools.config[name][self.name] = 1
            for child in self.children:
                setattr(child, name, value)
        if name == 'depth':
            for child in self.children:
                setattr(child, name, value + 1)

    def __iter__(self):
        return itertools.chain(iter(self.children), *map(iter, self.children))

    def __str__(self):
        return self._pprint()

    def _pprint(self, depth=0):
        s = '%s\n' % self.name
        for c in self.children:
            s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
        return s


def get_module_path(module, downloaded=False):
    """Return the path of the given module."""
    if os.path.exists(opj(ad, module)) or os.path.exists(opj(ad, '%s.zip' % module)):
        return opj(ad, module)

    if os.path.exists(opj(_ad, module)) or os.path.exists(opj(_ad, '%s.zip' % module)):
        return opj(_ad, module)
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
        files = tools.osutil.listdir(path, True)

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

def get_module_as_zip_from_module_directory(module_directory, b64enc=True, src=True):
    """Compress a module directory

    @param module_directory: The module directory
    @param base64enc: if True the function will encode the zip file with base64
    @param src: Integrate the source files

    @return: a stream to store in a file-like object
    """

    RE_exclude = re.compile('(?:^\..+\.swp$)|(?:\.py[oc]$)|(?:\.bak$)|(?:\.~.~$)', re.I)

    def _zippy(archive, path, src=True):
        path = os.path.abspath(path)
        base = os.path.basename(path)
        for f in tools.osutil.listdir(path, True):
            bf = os.path.basename(f)
            if not RE_exclude.search(bf) and (src or bf == '__terp__.py' or not bf.endswith('.py')):
                archive.write(os.path.join(path, f), os.path.join(base, f))

    archname = StringIO()
    archive = PyZipFile(archname, "w", ZIP_DEFLATED)
    archive.writepy(module_directory)
    _zippy(archive, module_directory, src=src)
    archive.close()
    val = archname.getvalue()
    archname.close()

    if b64enc:
        val = base64.encodestring(val)

    return val

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
        val = get_module_as_zip_from_module_directory(ap, b64enc, src)

    return val


def get_module_resource(module, *args):
    """Return the full path of a resource of the given module.

    @param module: the module
    @param args: the resource path components

    @return: absolute path to the resource
    """
    a = get_module_path(module)
    return a and opj(a, *args) or False


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

    return list(set(listdir(ad) + listdir(_ad)))

def get_modules_with_version():
    modules = get_modules()
    res = {}
    for module in modules:
        terp = get_module_resource(module, '__terp__.py')
        try:
            info = eval(tools.file_open(terp).read())
            res[module] = "%s.%s" % (release.major_version, info['version'])
        except Exception, e:
            continue
    return res

def create_graph(cr, module_list, force=None):
    graph = Graph()
    upgrade_graph(graph, cr, module_list, force)
    return graph

def upgrade_graph(graph, cr, module_list, force=None):
    if force is None:
        force = []
    packages = []
    len_graph = len(graph)
    for module in module_list:
        mod_path = get_module_path(module)
        terp_file = get_module_resource(module, '__terp__.py')
        if not mod_path or not terp_file:
            #Removed the query which was setting the module state uninstallable if module is not found
            continue

        if os.path.isfile(terp_file) or zipfile.is_zipfile(mod_path+'.zip'):
            try:
                info = eval(tools.file_open(terp_file).read())
            except:
                logger.notifyChannel('init', netsvc.LOG_ERROR, 'module %s: eval file %s' % (module, terp_file))
                raise
            if info.get('installable', True):
                packages.append((module, info.get('depends', []), info))


    dependencies = dict([(p, deps) for p, deps, data in packages])
    current, later = set([p for p, dep, data in packages]), set()
    while packages and current > later:
        package, deps, data = packages[0]

        # if all dependencies of 'package' are already in the graph, add 'package' in the graph
        if reduce(lambda x, y: x and y in graph, deps, True):
            if not package in current:
                packages.pop(0)
                continue
            later.clear()
            current.remove(package)
            graph.addNode(package, deps)
            node = Node(package, graph)
            node.data = data
            for kind in ('init', 'demo', 'update'):
                if package in tools.config[kind] or 'all' in tools.config[kind] or kind in force:
                    setattr(node, kind, True)
        else:
            later.add(package)
            packages.append((package, deps, data))
        packages.pop(0)

    graph.update_from_db(cr)

    for package in later:
        unmet_deps = filter(lambda p: p not in graph, dependencies[package])
        logger.notifyChannel('init', netsvc.LOG_ERROR, 'module %s: Unmet dependencies: %s' % (package, ', '.join(unmet_deps)))

    result = len(graph) - len_graph
    if result != len(module_list):
        logger.notifyChannel('init', netsvc.LOG_WARNING, 'Not all modules have loaded.')
    return result


def init_module_objects(cr, module_name, obj_list):
    logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: creating or updating database tables' % module_name)
    todo = []
    for obj in obj_list:
        try:
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


def register_class(m):
    """
    Register module named m, if not already registered
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

    try:
        zip_mod_path = mod_path + '.zip'
        if not os.path.isfile(zip_mod_path):
            fm = imp.find_module(m, [ad, _ad])
            try:
                imp.load_module(m, *fm)
            finally:
                if fm[0]:
                    fm[0].close()
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

        from tools.parse_version import parse_version

        parsed_installed_version = parse_version(pkg.installed_version or '')
        current_version = parse_version(convert_version(pkg.data.get('version', '0')))

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


def load_module_graph(cr, graph, status=None, perform_checks=True, **kwargs):
    # **kwargs is passed directly to convert_xml_import
    if not status:
        status = {}

    status = status.copy()
    package_todo = []
    statusi = 0
    pool = pooler.get_pool(cr.dbname)

    migrations = MigrationManager(cr, graph)

    has_updates = False
    modobj = None

    for package in graph:
        logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: loading objects' % package.name)
        migrations.migrate_module(package, 'pre')
        register_class(package.name)
        modules = pool.instanciate(package.name, cr)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_objects(cr, package.name, modules)
        cr.commit()
        
    for package in graph:
        status['progress'] = (float(statusi)+0.1) / len(graph)
        m = package.name
        mid = package.id

        if modobj is None:
            modobj = pool.get('ir.module.module')

        if modobj and perform_checks:
            modobj.check(cr, 1, [mid])

        idref = {}
        status['progress'] = (float(statusi)+0.4) / len(graph)

        mode = 'update'
        if hasattr(package, 'init') or package.state == 'to install':
            mode = 'init'

        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            has_updates = True
            for kind in ('init', 'update'):
                if package.state=='to upgrade':
                    # upgrading the module information
                    modobj.write(cr, 1, [mid], {
                    'description': package.data.get('description', ''),
                    'shortdesc': package.data.get('name', ''),
                    'author': package.data.get('author', 'Unknown'),
                    'website': package.data.get('website', ''),
                    'license': package.data.get('license', 'GPL-2'),
                    'certificate': package.data.get('certificate') or None,
                    })
                for filename in package.data.get('%s_xml' % kind, []):
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: loading %s' % (m, filename))
                    name, ext = os.path.splitext(filename)
                    fp = tools.file_open(opj(m, filename))
                    if ext == '.csv':
                        tools.convert_csv_import(cr, m, os.path.basename(filename), fp.read(), idref, mode=mode)
                    elif ext == '.sql':
                        queries = fp.read().split(';')
                        for query in queries:
                            new_query = ' '.join(query.split())
                            if new_query:
                                cr.execute(new_query)
                    else:
                        tools.convert_xml_import(cr, m, fp, idref, mode=mode, **kwargs)
                    fp.close()
            if hasattr(package, 'demo') or (package.dbdemo and package.state != 'installed'):
                status['progress'] = (float(statusi)+0.75) / len(graph)
                for xml in package.data.get('demo_xml', []):
                    name, ext = os.path.splitext(xml)
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'module %s: loading %s' % (m, xml))
                    fp = tools.file_open(opj(m, xml))
                    if ext == '.csv':
                        tools.convert_csv_import(cr, m, os.path.basename(xml), fp.read(), idref, mode=mode, noupdate=True)
                    else:
                        tools.convert_xml_import(cr, m, fp, idref, mode=mode, noupdate=True, **kwargs)
                    fp.close()
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, mid))
            package_todo.append(package.name)

            migrations.migrate_module(package, 'post')

            if modobj:
                ver = release.major_version + '.' + package.data.get('version', '1.0')
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

    cr.execute('select model from ir_model where state=%s', ('manual',))
    for model in cr.dictfetchall():
        pool.get('ir.model').instanciate(cr, 1, model['model'], {})

    pool.get('ir.model.data')._process_end(cr, 1, package_todo)
    cr.commit()

    return has_updates

def load_modules(db, force_demo=False, status=None, update_module=False):
    if not status:
        status = {}

    cr = db.cursor()
    if cr:
       cr.execute("SELECT relname FROM pg_class WHERE relkind='r' AND relname='ir_module_module'")
       if len(cr.fetchall())==0:    
           logger.notifyChannel("init", netsvc.LOG_INFO, "init db")
           tools.init_db(cr)
           # in that case, force --init=all
           tools.config["init"]["all"] = 1
           tools.config['update']['all'] = 1
           if not tools.config['without_demo']:
               tools.config["demo"]['all'] = 1 
    force = []
    if force_demo:
        force.append('demo')
    pool = pooler.get_pool(cr.dbname)
    try:
        report = tools.assertion_report()
        # NOTE: Try to also load the modules that have been marked as uninstallable previously...
        STATES_TO_LOAD = ['installed', 'to upgrade', 'uninstallable']
        graph = create_graph(cr, ['base'], force)

        has_updates = load_module_graph(cr, graph, status, perform_checks=(not update_module), report=report)

        if update_module:
            modobj = pool.get('ir.module.module')
            logger.notifyChannel('init', netsvc.LOG_INFO, 'updating modules list')
            if ('base' in tools.config['init']) or ('base' in tools.config['update']):
                modobj.update_list(cr, 1)

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

        loop_guardrail = 0
        while True:
            loop_guardrail += 1
            if loop_guardrail > 100:
                raise ProgrammingError()
            cr.execute("SELECT name from ir_module_module WHERE state in %s",
                       (tuple(STATES_TO_LOAD),)
                      )

            module_list = [name for (name,) in cr.fetchall() if name not in graph]
            if not module_list:
                break

            new_modules_in_graph = upgrade_graph(graph, cr, module_list, force)
            if new_modules_in_graph == 0:
                # nothing to load
                break
            logger.notifyChannel('init', netsvc.LOG_DEBUG, 'Updating graph with %d more modules' % (len(module_list)))
            r = load_module_graph(cr, graph, status, report=report)
            has_updates = has_updates or r

        if has_updates:
            cr.execute("""select model,name from ir_model where id not in (select model_id from ir_model_access)""")
            for (model, name) in cr.fetchall():
                logger.notifyChannel('init', netsvc.LOG_WARNING, 'object %s (%s) has no access rules!' % (model, name))

            cr.execute("SELECT model from ir_model")
            for (model,) in cr.fetchall():
                obj = pool.get(model)
                if obj:
                    obj._check_removed_columns(cr, log=True)

        if report.get_report():
            logger.notifyChannel('init', netsvc.LOG_INFO, report)

        for kind in ('init', 'demo', 'update'):
            tools.config[kind] = {}

        cr.commit()
        if update_module:
            cr.execute("select id,name from ir_module_module where state=%s", ('to remove',))
            for mod_id, mod_name in cr.fetchall():
                cr.execute('select model,res_id from ir_model_data where noupdate=%s and module=%s order by id desc', (False, mod_name,))
                for rmod, rid in cr.fetchall():
                    uid = 1
                    pool.get(rmod).unlink(cr, uid, [rid])
                cr.execute('delete from ir_model_data where noupdate=%s and module=%s', (False, mod_name,))
                cr.commit()
            #
            # TODO: remove menu without actions of children
            #
            while True:
                cr.execute('''delete from
                        ir_ui_menu
                    where
                        (id not in (select parent_id from ir_ui_menu where parent_id is not null))
                    and
                        (id not in (select res_id from ir_values where model='ir.ui.menu'))
                    and
                        (id not in (select res_id from ir_model_data where model='ir.ui.menu'))''')
                cr.commit()
                if not cr.rowcount:
                    break
                else:
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'removed %d unused menus' % (cr.rowcount,))

            cr.execute("update ir_module_module set state=%s where state=%s", ('uninstalled', 'to remove',))
            cr.commit()
    finally:
        cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
