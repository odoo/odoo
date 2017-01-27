# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import imp
import importlib
import inspect
import itertools
import logging
import os
import pkg_resources
import re
import sys
import time
import types
import unittest
import threading
from operator import itemgetter
from os.path import join as opj


import openerp
import openerp.tools as tools
import openerp.release as release
from openerp import SUPERUSER_ID
from openerp.tools.safe_eval import safe_eval as eval

MANIFEST = '__openerp__.py'
README = ['README.rst', 'README.md', 'README.txt']

_logger = logging.getLogger(__name__)

# addons path as a list
ad_paths = []
hooked = False

# Modules already loaded
loaded = []

class AddonsHook(object):
    """ Makes modules accessible through openerp.addons.* and odoo.addons.*
    """
    def find_module(self, name, path):
        if name.startswith(('odoo.addons.', 'openerp.addons.'))\
                and name.count('.') == 2:
            return self

    def load_module(self, name):
        assert name not in sys.modules

        # get canonical names
        odoo_name = re.sub(r'^openerp.addons.(\w+)$', r'odoo.addons.\g<1>', name)
        openerp_name = re.sub(r'^odoo.addons.(\w+)$', r'openerp.addons.\g<1>', odoo_name)

        assert odoo_name not in sys.modules
        assert openerp_name not in sys.modules

        # get module name in addons paths
        _1, _2, addon_name = name.split('.')
        # load module
        f, path, (_suffix, _mode, type_) = imp.find_module(addon_name, ad_paths)
        if f: f.close()

        # TODO: fetch existing module from sys.modules if reloads permitted
        # create empty openerp.addons.* module, set name
        new_mod = types.ModuleType(openerp_name)
        new_mod.__loader__ = self

        # module top-level can only be a package
        assert type_ == imp.PKG_DIRECTORY, "Odoo addon top-level must be a package"
        modfile = opj(path, '__init__.py')
        new_mod.__file__ = modfile
        new_mod.__path__ = [path]
        new_mod.__package__ = openerp_name

        # both base and alias should be in sys.modules to handle recursive and
        # corecursive situations
        sys.modules[openerp_name] = sys.modules[odoo_name] = new_mod

        # execute source in context of module *after* putting everything in
        # sys.modules, so recursive import works
        execfile(modfile, new_mod.__dict__)

        # people import openerp.addons and expect openerp.addons.<module> to work
        setattr(openerp.addons, addon_name, new_mod)

        return sys.modules[name]
# need to register loader with setuptools as Jinja relies on it when using
# PackageLoader
pkg_resources.register_loader_type(AddonsHook, pkg_resources.DefaultProvider)

class OdooHook(object):
    """ Makes odoo package also available as openerp
    """

    def find_module(self, name, path=None):
        # openerp.addons.<identifier> should already be matched by AddonsHook,
        # only framework and subdirectories of modules should match
        if re.match(r'^odoo\b', name):
            return self

    def load_module(self, name):
        assert name not in sys.modules

        canonical = re.sub(r'^odoo(.*)', r'openerp\g<1>', name)

        if canonical in sys.modules:
            mod = sys.modules[canonical]
        else:
            # probable failure: canonical execution calling old naming -> corecursion
            mod = importlib.import_module(canonical)

        # just set the original module at the new location. Don't proxy,
        # it breaks *-import (unless you can find how `from a import *` lists
        # what's supposed to be imported by `*`, and manage to override it)
        sys.modules[name] = mod

        return sys.modules[name]

def initialize_sys_path():
    """
    Setup an import-hook to be able to import OpenERP addons from the different
    addons paths.

    This ensures something like ``import crm`` (or even
    ``import openerp.addons.crm``) works even if the addons are not in the
    PYTHONPATH.
    """
    global ad_paths
    global hooked

    dd = tools.config.addons_data_dir
    if os.access(dd, os.R_OK) and dd not in ad_paths:
        ad_paths.append(dd)

    for ad in tools.config['addons_path'].split(','):
        ad = os.path.abspath(tools.ustr(ad.strip()))
        if ad not in ad_paths:
            ad_paths.append(ad)

    # add base module path
    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addons'))
    if base_path not in ad_paths:
        ad_paths.append(base_path)

    if not hooked:
        sys.meta_path.append(AddonsHook())
        sys.meta_path.append(OdooHook())
        hooked = True

def get_module_path(module, downloaded=False, display_warning=True):
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    initialize_sys_path()
    for adp in ad_paths:
        if os.path.exists(opj(adp, module, MANIFEST)) or os.path.exists(opj(adp, '%s.zip' % module)):
            return opj(adp, module)

    if downloaded:
        return opj(tools.config.addons_data_dir, module)
    if display_warning:
        _logger.warning('module %s: module not found', module)
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

    files = openerp.tools.osutil.listdir(path, True)

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

def get_resource_path(module, *args):
    """Return the full path of a resource of the given module.

    :param module: module name
    :param list(str) args: resource path components within module

    :rtype: str
    :return: absolute path to the resource

    TODO make it available inside on osv object (self.get_resource_path)
    """
    mod_path = get_module_path(module)
    if not mod_path: return False
    resource_path = opj(mod_path, *args)
    if os.path.isdir(mod_path):
        # the module is a directory - ignore zip behavior
        if os.path.exists(resource_path):
            return resource_path
    return False

# backwards compatibility
get_module_resource = get_resource_path

def get_resource_from_path(path):
    """Tries to extract the module name and the resource's relative path
    out of an absolute resource path.

    If operation is successfull, returns a tuple containing the module name, the relative path
    to the resource using '/' as filesystem seperator[1] and the same relative path using
    os.path.sep seperators.

    [1] same convention as the resource path declaration in manifests

    :param path: absolute resource path

    :rtype: tuple
    :return: tuple(module_name, relative_path, os_relative_path) if possible, else None
    """
    resource = False
    for adpath in ad_paths:
        # force trailing separator
        adpath = os.path.join(adpath, "")
        if os.path.commonprefix([adpath, path]) == adpath:
            resource = path.replace(adpath, "", 1)
            break

    if resource:
        relative = resource.split(os.path.sep)
        if not relative[0]:
            relative.pop(0)
        module = relative.pop(0)
        return (module, '/'.join(relative), os.path.sep.join(relative))
    return None

def get_module_icon(module):
    iconpath = ['static', 'description', 'icon.png']
    if get_module_resource(module, *iconpath):
        return ('/' + module + '/') + '/'.join(iconpath)
    return '/base/'  + '/'.join(iconpath)

def get_module_root(path):
    """
    Get closest module's root begining from path

        # Given:
        # /foo/bar/module_dir/static/src/...

        get_module_root('/foo/bar/module_dir/static/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar/module_dir/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar')
        # returns None

    @param path: Path from which the lookup should start

    @return:  Module root path or None if not found
    """
    while not os.path.exists(os.path.join(path, MANIFEST)):
        new_path = os.path.abspath(os.path.join(path, os.pardir))
        if path == new_path:
            return None
        path = new_path
    return path

def load_information_from_description_file(module, mod_path=None):
    """
    :param module: The name of the module (sale, purchase, ...)
    :param mod_path: Physical path of module, if not providedThe name of the module (sale, purchase, ...)
    """

    if not mod_path:
        mod_path = get_module_path(module)
    terp_file = mod_path and opj(mod_path, MANIFEST) or False
    if terp_file:
        info = {}
        if os.path.isfile(terp_file):
            # default values for descriptor
            info = {
                'application': False,
                'author': 'Odoo S.A.',
                'auto_install': False,
                'category': 'Uncategorized',
                'depends': [],
                'description': '',
                'icon': get_module_icon(module),
                'installable': True,
                'license': 'LGPL-3',
                'post_load': None,
                'version': '1.0',
                'web': False,
                'website': 'https://www.odoo.com',
                'sequence': 100,
                'summary': '',
            }
            info.update(itertools.izip(
                'depends data demo test init_xml update_xml demo_xml'.split(),
                iter(list, None)))

            f = tools.file_open(terp_file)
            try:
                info.update(eval(f.read()))
            finally:
                f.close()

            if not info.get('description'):
                readme_path = [opj(mod_path, x) for x in README
                               if os.path.isfile(opj(mod_path, x))]
                if readme_path:
                    readme_text = tools.file_open(readme_path[0]).read()
                    info['description'] = readme_text

            if 'active' in info:
                # 'active' has been renamed 'auto_install'
                info['auto_install'] = info['active']

            info['version'] = adapt_version(info['version'])
            return info

    #TODO: refactor the logger in this file to follow the logging guidelines
    #      for 6.0
    _logger.debug('module %s: no %s file found.', module, MANIFEST)
    return {}

def init_models(models, cr, context):
    """ Initialize a list of models.

    Call methods ``_auto_init``, ``init``, and ``_auto_end`` on each model to
    create or update the database tables supporting the models.

    The context may contain the following items:
     - ``module``: the name of the module being installed/updated, if any;
     - ``update_custom_fields``: whether custom fields should be updated.

    """
    if 'module' in context:
        _logger.info('module %s: creating or updating database tables', context['module'])
    context = dict(context, todo=[])
    models = [model.browse(cr, SUPERUSER_ID, [], context) for model in models]
    for model in models:
        model._auto_init()
        model.init()
        cr.commit()
    for model in models:
        model._auto_end()
        cr.commit()
    for _, func, args in sorted(context['todo'], key=itemgetter(0)):
        func(cr, *args)
    if models:
        models[0].recompute()
    cr.commit()

def load_openerp_module(module_name):
    """ Load an OpenERP module, if not already loaded.

    This loads the module and register all of its models, thanks to either
    the MetaModel metaclass, or the explicit instantiation of the model.
    This is also used to load server-wide module (i.e. it is also used
    when there is no model to register).
    """
    global loaded
    if module_name in loaded:
        return

    initialize_sys_path()
    try:
        mod_path = get_module_path(module_name)
        __import__('openerp.addons.' + module_name)

        # Call the module's post-load hook. This can done before any model or
        # data has been initialized. This is ok as the post-load hook is for
        # server-wide (instead of registry-specific) functionalities.
        info = load_information_from_description_file(module_name)
        if info['post_load']:
            getattr(sys.modules['openerp.addons.' + module_name], info['post_load'])()

    except Exception, e:
        msg = "Couldn't load module %s" % (module_name)
        _logger.critical(msg)
        _logger.critical(e)
        raise
    else:
        loaded.append(module_name)

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
            manifest_name = opj(dir, name, MANIFEST)
            zipfile_name = opj(dir, name)
            return os.path.isfile(manifest_name)
        return map(clean, filter(is_really_module, os.listdir(dir)))

    plist = []
    initialize_sys_path()
    for ad in ad_paths:
        plist.extend(listdir(ad))
    return list(set(plist))

def get_modules_with_version():
    modules = get_modules()
    res = dict.fromkeys(modules, adapt_version('1.0'))
    for module in modules:
        try:
            info = load_information_from_description_file(module)
            res[module] = info['version']
        except Exception:
            continue
    return res

def adapt_version(version):
    serie = release.major_version
    if version == serie or not version.startswith(serie + '.'):
        version = '%s.%s' % (serie, version)
    return version

def get_test_modules(module):
    """ Return a list of module for the addons potentially containing tests to
    feed unittest.TestLoader.loadTestsFromModule() """
    # Try to import the module
    modpath = 'openerp.addons.' + module
    try:
        mod = importlib.import_module('.tests', modpath)
    except Exception, e:
        # If module has no `tests` sub-module, no problem.
        if str(e) != 'No module named tests':
            _logger.exception('Can not `import %s`.', module)
        return []

    if hasattr(mod, 'fast_suite') or hasattr(mod, 'checks'):
        _logger.warn(
            "Found deprecated fast_suite or checks attribute in test module "
            "%s. These have no effect in or after version 8.0.",
            mod.__name__)

    result = [mod_obj for name, mod_obj in inspect.getmembers(mod, inspect.ismodule)
              if name.startswith('test_')]
    return result

# Use a custom stream object to log the test executions.
class TestStream(object):
    def __init__(self, logger_name='openerp.tests'):
        self.logger = logging.getLogger(logger_name)
        self.r = re.compile(r'^-*$|^ *... *$|^ok$')
    def flush(self):
        pass
    def write(self, s):
        if self.r.match(s):
            return
        first = True
        level = logging.ERROR if s.startswith(('ERROR', 'FAIL', 'Traceback')) else logging.INFO
        for c in s.splitlines():
            if not first:
                c = '` ' + c
            first = False
            self.logger.log(level, c)

current_test = None

def runs_at(test, hook, default):
    # by default, tests do not run post install
    test_runs = getattr(test, hook, default)

    # for a test suite, we're done
    if not isinstance(test, unittest.TestCase):
        return test_runs

    # otherwise check the current test method to see it's been set to a
    # different state
    method = getattr(test, test._testMethodName)
    return getattr(method, hook, test_runs)

runs_at_install = functools.partial(runs_at, hook='at_install', default=True)
runs_post_install = functools.partial(runs_at, hook='post_install', default=False)

def run_unit_tests(module_name, dbname, position=runs_at_install):
    """
    :returns: ``True`` if all of ``module_name``'s tests succeeded, ``False``
              if any of them failed.
    :rtype: bool
    """
    global current_test
    current_test = module_name
    mods = get_test_modules(module_name)
    threading.currentThread().testing = True
    r = True
    for m in mods:
        tests = unwrap_suite(unittest.TestLoader().loadTestsFromModule(m))
        suite = unittest.TestSuite(itertools.ifilter(position, tests))

        if suite.countTestCases():
            t0 = time.time()
            t0_sql = openerp.sql_db.sql_counter
            _logger.info('%s running tests.', m.__name__)
            result = unittest.TextTestRunner(verbosity=2, stream=TestStream(m.__name__)).run(suite)
            if time.time() - t0 > 5:
                _logger.log(25, "%s tested in %.2fs, %s queries", m.__name__, time.time() - t0, openerp.sql_db.sql_counter - t0_sql)
            if not result.wasSuccessful():
                r = False
                _logger.error("Module %s: %d failures, %d errors", module_name, len(result.failures), len(result.errors))

    current_test = None
    threading.currentThread().testing = False
    return r

def unwrap_suite(test):
    """
    Attempts to unpack testsuites (holding suites or cases) in order to
    generate a single stream of terminals (either test cases or customized
    test suites). These can then be checked for run/skip attributes
    individually.

    An alternative would be to use a variant of @unittest.skipIf with a state
    flag of some sort e.g. @unittest.skipIf(common.runstate != 'at_install'),
    but then things become weird with post_install as tests should *not* run
    by default there
    """
    if isinstance(test, unittest.TestCase):
        yield test
        return

    subtests = list(test)
    # custom test suite (no test cases)
    if not len(subtests):
        yield test
        return

    for item in itertools.chain.from_iterable(
            itertools.imap(unwrap_suite, subtests)):
        yield item
