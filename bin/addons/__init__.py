# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
from sets import Set

import osv
import tools
import tools.osutil
import pooler


import netsvc
from osv import fields

import zipfile
import release

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

    def __iter__(self):
        level = 0
        done = Set(self.keys())
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
        if not hasattr(self, 'childs'):
            self.childs = []
        if not hasattr(self, 'depth'):
            self.depth = 0

    def addChild(self, name):
        node = Node(name, self.graph)
        node.depth = self.depth + 1
        if node not in self.childs:
            self.childs.append(node)
        for attr in ('init', 'update', 'demo'):
            if hasattr(self, attr):
                setattr(node, attr, True)
        self.childs.sort(lambda x,y: cmp(x.name, y.name))

    def hasChild(self, name):
        return Node(name, self.graph) in self.childs or \
                bool([c for c in self.childs if c.hasChild(name)])

    def __setattr__(self, name, value):
        super(Singleton, self).__setattr__(name, value)
        if name in ('init', 'update', 'demo'):
            tools.config[name][self.name] = 1
            for child in self.childs:
                setattr(child, name, value)
        if name == 'depth':
            for child in self.childs:
                setattr(child, name, value + 1)

    def __iter__(self):
        return itertools.chain(iter(self.childs), *map(iter, self.childs))

    def __str__(self):
        return self._pprint()

    def _pprint(self, depth=0):
        s = '%s\n' % self.name
        for c in self.childs:
            s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
        return s

def get_module_path(module):
    """Return the path of the given module.
    """

    if os.path.exists(opj(ad, module)) or os.path.exists(opj(ad, '%s.zip' % module)):
        return opj(ad, module)

    if os.path.exists(opj(_ad, module)) or os.path.exists(opj(_ad, '%s.zip' % module)):
        return opj(_ad, module)

    logger.notifyChannel('init', netsvc.LOG_WARNING, 'addon %s: module not found' % (module,))
    return False
    raise IOError, 'Module not found : %s' % module


def get_module_filetree(module, dir='.'):
    path = get_module_path(module)
    if not path:
        return False
    
    dir = os.path.normpath(dir)
    if dir == '.': dir = ''
    if dir.startswith('..') or dir[0] == '/':
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
        f = f[len(dir)+int(not dir.endswith('/')):]
        lst = f.split(os.sep)
        current = tree
        while len(lst) != 1:
            current = current.setdefault(lst.pop(0), {})
        current[lst.pop(0)] = None
    
    return tree

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
        return map(clean, os.listdir(dir))

    return list(set(listdir(ad) + listdir(_ad)))

def create_graph(module_list, force=None):
    if not force:
        force=[]
    graph = Graph()
    packages = []

    for module in module_list:
        try:
            mod_path = get_module_path(module)
            if not mod_path:
                continue
        except IOError:
            continue
        terp_file = get_module_resource(module, '__terp__.py')
        if not terp_file: continue
        if os.path.isfile(terp_file) or zipfile.is_zipfile(mod_path+'.zip'):
            try:
                info = eval(tools.file_open(terp_file).read())
            except:
                logger.notifyChannel('init', netsvc.LOG_ERROR, 'addon %s: eval file %s' % (module, terp_file))
                raise
            if info.get('installable', True):
                packages.append((module, info.get('depends', []), info))
    
    dependencies = dict([(p, deps) for p, deps, data in packages])
    current, later = Set([p for p, dep, data in packages]), Set()
    while packages and current > later:
        package, deps, data = packages[0]

        # if all dependencies of 'package' are already in the graph, add 'package' in the graph
        if reduce(lambda x,y: x and y in graph, deps, True):
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
    
    for package in later:
        unmet_deps = filter(lambda p: p not in graph, dependencies[package])
        logger.notifyChannel('init', netsvc.LOG_ERROR, 'addon %s: Unmet dependencies: %s' % (package, ', '.join(unmet_deps)))

    return graph

def init_module_objects(cr, module_name, obj_list):
    pool = pooler.get_pool(cr.dbname)
    logger.notifyChannel('init', netsvc.LOG_INFO, 'addon %s: creating or updating database tables' % module_name)
    for obj in obj_list:
        if hasattr(obj, 'init'):
            obj.init(cr)
        obj._auto_init(cr, {'module': module_name})
        cr.commit()

#
# Register module named m, if not already registered
# 
def register_class(m):
    global loaded
    if m in loaded:
        return
    logger.notifyChannel('init', netsvc.LOG_INFO, 'addon %s: registering classes' % m)
    loaded.append(m)
    mod_path = get_module_path(m)
    if not os.path.isfile(mod_path+'.zip'):
        imp.load_module(m, *imp.find_module(m, [ad, _ad]))
    else:
        import zipimport
        try:
            zimp = zipimport.zipimporter(mod_path+'.zip')
            zimp.load_module(m)
        except zipimport.ZipImportError:
            logger.notifyChannel('init', netsvc.LOG_ERROR, 'Couldn\'t find module %s' % m)


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
                
            mapping = {'module': {'module': pkg.name, 'rootdir': opj('migrations')},
                       'maintenance': {'module': 'base', 'rootdir': opj('maintenance', 'migrations', pkg.name)},
                      }

            for x in mapping.keys():
                if version in m[x]:
                    for f in m[x][version]:
                        if m[x][version][f] is not None:
                            continue
                        if not f.startswith(stage + '-'):
                            continue
                        lst.append((mapping[x]['module'], opj(mapping[x]['rootdir'], version, f)))
            return lst

        def mergedict(a,b):
            a = a.copy()
            a.update(b)
            return a

        from tools.parse_version import parse_version

        parsed_installed_version = parse_version(pkg.installed_version)
        current_version = parse_version(convert_version(pkg.data.get('version', '0')))
        
        versions = _get_migration_versions(pkg)

        for version in versions:
            if parsed_installed_version < parse_version(convert_version(version)) <= current_version:

                strfmt = {'addon': pkg.name,
                          'stage': stage,
                          'version': stageformat[stage] % version,
                          }
                
                for modulename, pyfile in _get_migration_files(pkg, version, stage):
                    name, ext = os.path.splitext(os.path.basename(pyfile))
                    if ext.lower() != '.py':
                        continue
                    fp = tools.file_open(opj(modulename, pyfile))
                    mod = None
                    try:
                        mod = imp.load_source(name, pyfile, fp)
                        logger.notifyChannel('migration', netsvc.LOG_INFO, 'addon %(addon)s: Running migration %(version)s %(name)s"' % mergedict({'name': mod.__name__},strfmt))
                        mod.migrate(self.cr, pkg.installed_version)
                    except ImportError:
                        logger.notifyChannel('migration', netsvc.LOG_ERROR, 'addon %(addon)s: Unable to load %(stage)-migration file %(file)s' % mergedict({'file': opj(modulename,pyfile)}, strfmt))
                        raise
                    except AttributeError:
                        logger.notifyChannel('migration', netsvc.LOG_ERROR, 'addon %(addon)s: Each %(stage)-migration file must have a "migrate(cr, installed_version)" function' % strfmt)
                    except:
                        raise
                    fp.close()
                    del mod
    

def load_module_graph(cr, graph, status=None, check_access_rules=True, **kwargs):
    # **kwargs is passed directly to convert_xml_import
    if not status:
        status={}

    status = status.copy()
    package_todo = []
    statusi = 0
    pool = pooler.get_pool(cr.dbname)


    # update the graph with values from the database (if exist)
    ## First, we set the default values for each package in graph
    additional_data = dict.fromkeys([p.name for p in graph], {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None})
    ## Then we get the values from the database
    cr.execute('SELECT name, id, state, demo AS dbdemo, latest_version AS installed_version'
               '  FROM ir_module_module'
               ' WHERE name in (%s)' % (','.join(['%s'] * len(graph))),
                additional_data.keys()
               )

    ## and we update the default values with values from the database
    additional_data.update(dict([(x.pop('name'), x) for x in cr.dictfetchall()]))

    for package in graph:
        for k, v in additional_data[package.name].items():
            setattr(package, k, v)
    
    migrations = MigrationManager(cr, graph)

    for package in graph:
        status['progress'] = (float(statusi)+0.1)/len(graph)
        m = package.name
        mid = package.id

        migrations.migrate_module(package, 'pre')

        register_class(m)
        logger.notifyChannel('init', netsvc.LOG_INFO, 'addon %s' % m)
        modules = pool.instanciate(m, cr)

        idref = {}
        status['progress'] = (float(statusi)+0.4)/len(graph)
        if hasattr(package, 'init') or hasattr(package, 'update') or package.state in ('to install', 'to upgrade'):
            init_module_objects(cr, m, modules)
            for kind in ('init', 'update'):
                for filename in package.data.get('%s_xml' % kind, []):
                    mode = 'update'
                    if hasattr(package, 'init') or package.state=='to install':
                        mode = 'init'
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'addon %s: loading %s' % (m, filename))
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
                status['progress'] = (float(statusi)+0.75)/len(graph)
                for xml in package.data.get('demo_xml', []):
                    name, ext = os.path.splitext(xml)
                    logger.notifyChannel('init', netsvc.LOG_INFO, 'addon %s: loading %s' % (m, xml))
                    fp = tools.file_open(opj(m, xml))
                    if ext == '.csv':
                        tools.convert_csv_import(cr, m, os.path.basename(xml), fp.read(), idref, noupdate=True)
                    else:
                        tools.convert_xml_import(cr, m, fp, idref, noupdate=True, **kwargs)
                    fp.close()
                cr.execute('update ir_module_module set demo=%s where id=%s', (True, mid))
            package_todo.append(package.name)
            ver = release.major_version + '.' + package.data.get('version', '1.0')
            # update the installed version in database...
            cr.execute("update ir_module_module set state='installed', latest_version=%s where id=%s", (ver, mid,))
            cr.commit()

            # Set new modules and dependencies
            modobj = pool.get('ir.module.module')

            # Update translations for all installed languages
            if modobj:
                modobj.update_translations(cr, 1, [mid], None)
                cr.commit()
        
            
            migrations.migrate_module(package, 'post')

        statusi+=1

    if check_access_rules:
        cr.execute("""select model,name from ir_model where id not in (select model_id from ir_model_access)""")
        for (model,name) in cr.fetchall():
            logger.notifyChannel('init', netsvc.LOG_WARNING, 'addon object %s (%s) has no access rules!' % (model,name))


    pool = pooler.get_pool(cr.dbname)
    cr.execute('select model from ir_model where state=%s', ('manual',))
    for model in cr.dictfetchall():
        pool.get('ir.model').instanciate(cr, 1, model['model'], {})

    pool.get('ir.model.data')._process_end(cr, 1, package_todo)
    cr.commit()

def load_modules(db, force_demo=False, status=None, update_module=False):
    if not status:
        status={}
    cr = db.cursor()
    force = []
    if force_demo:
        force.append('demo')
    pool = pooler.get_pool(cr.dbname)
    report = tools.assertion_report()
    if update_module:
        basegraph = create_graph(['base'], force)
        load_module_graph(cr, basegraph, status, check_access_rules=False, report=report)
        
        modobj = pool.get('ir.module.module')
        modobj.update_list(cr, 1)
        
        if tools.config['init']: 
            ids = modobj.search(cr, 1, ['&', ('state', '=', 'uninstalled'), ('name', 'in', tools.config['init'])])
            if ids:
                modobj.button_install(cr, 1, ids)

        ids = modobj.search(cr, 1, ['&', '!', ('name', '=', 'base'), ('state', 'in', ('installed', 'to upgrade'))])
        if ids:
            modobj.button_upgrade(cr, 1, ids)
        
        cr.execute("select name from ir_module_module where state in ('installed', 'to install', 'to upgrade','to remove')")
    else:
        cr.execute("select name from ir_module_module where state in ('installed', 'to upgrade', 'to remove')")
    module_list = [name for (name,) in cr.fetchall()]
    graph = create_graph(module_list, force)
    
    # the 'base' module has already been updated
    base = graph['base']
    for kind in ('init', 'demo', 'update'):
        if hasattr(base, kind):
            delattr(base, kind)

    load_module_graph(cr, graph, status, report=report)
    if report.get_report():
        logger.notifyChannel('init', netsvc.LOG_INFO, 'assert: %s' % report)

    for kind in ('init', 'demo', 'update'):
        tools.config[kind]={}

    cr.commit()
    if update_module:
        cr.execute("select id,name from ir_module_module where state in ('to remove')")
        for mod_id, mod_name in cr.fetchall():
            pool = pooler.get_pool(cr.dbname)
            cr.execute('select model,res_id from ir_model_data where not noupdate and module=%s order by id desc', (mod_name,))
            for rmod,rid in cr.fetchall():
                #
                # TO BE Improved:
                #   I can not use the class_pool has _table could be defined in __init__
                #   and I can not use the pool has the module could not be loaded in the pool
                #
                uid = 1
                pool.get(rmod).unlink(cr, uid, [rid])
            cr.commit()
        #
        # TODO: remove menu without actions of childs
        #
        cr.execute('''delete from
                ir_ui_menu
            where
                (id not in (select parent_id from ir_ui_menu where parent_id is not null))
            and
                (id not in (select res_id from ir_values where model='ir.ui.menu'))
            and
                (id not in (select res_id from ir_model_data where model='ir.ui.menu'))''')

        cr.execute("update ir_module_module set state=%s where state in ('to remove')", ('uninstalled', ))
        cr.commit()
        pooler.restart_pool(cr.dbname)
    cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

