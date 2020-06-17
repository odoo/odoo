# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import collections
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
import warnings
from operator import itemgetter
from os.path import join as opj

import odoo
import odoo.tools as tools
import odoo.release as release
from odoo import SUPERUSER_ID, api
from odoo.tools import pycompat
from odoo.tools.misc import mute_logger

MANIFEST_NAMES = ('__manifest__.py', '__openerp__.py')
README = ['README.rst', 'README.md', 'README.txt']

_logger = logging.getLogger(__name__)

# addons path as a list
# ad_paths is a deprecated alias, please use odoo.addons.__path__
@tools.lazy
def ad_paths():
    warnings.warn(
        '"odoo.modules.module.ad_paths" is a deprecated proxy to '
        '"odoo.addons.__path__".', DeprecationWarning, stacklevel=2)
    return odoo.addons.__path__

# Modules already loaded
loaded = []

class AddonsHook(object):
    """ Makes modules accessible through openerp.addons.* """

    def find_module(self, name, path=None):
        if name.startswith('openerp.addons.') and name.count('.') == 2:
            warnings.warn(
                '"openerp.addons" is a deprecated alias to "odoo.addons".',
                DeprecationWarning, stacklevel=2)
            return self

    def load_module(self, name):
        assert name not in sys.modules

        odoo_name = re.sub(r'^openerp.addons.(\w+)$', r'odoo.addons.\g<1>', name)

        odoo_module = sys.modules.get(odoo_name)
        if not odoo_module:
            odoo_module = importlib.import_module(odoo_name)

        sys.modules[name] = odoo_module

        return odoo_module

# need to register loader with setuptools as Jinja relies on it when using
# PackageLoader
pkg_resources.register_loader_type(AddonsHook, pkg_resources.DefaultProvider)

class OdooHook(object):
    """ Makes odoo package also available as openerp """

    def find_module(self, name, path=None):
        # openerp.addons.<identifier> should already be matched by AddonsHook,
        # only framework and subdirectories of modules should match
        if re.match(r'^openerp\b', name):
            warnings.warn(
                'openerp is a deprecated alias to odoo.',
                DeprecationWarning, stacklevel=2)
            return self

    def load_module(self, name):
        assert name not in sys.modules

        canonical = re.sub(r'^openerp(.*)', r'odoo\g<1>', name)

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
    ``import odoo.addons.crm``) works even if the addons are not in the
    PYTHONPATH.
    """
    # hook odoo.addons on data dir
    dd = os.path.normcase(tools.config.addons_data_dir)
    if os.access(dd, os.R_OK) and dd not in odoo.addons.__path__:
        odoo.addons.__path__.append(dd)

    # hook odoo.addons on addons paths
    for ad in tools.config['addons_path'].split(','):
        ad = os.path.normcase(os.path.abspath(tools.ustr(ad.strip())))
        if ad not in odoo.addons.__path__:
            odoo.addons.__path__.append(ad)

    # hook odoo.addons on base module path
    base_path = os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addons')))
    if base_path not in odoo.addons.__path__ and os.path.isdir(base_path):
        odoo.addons.__path__.append(base_path)

    # hook odoo.upgrade on upgrade-path
    from odoo import upgrade
    legacy_upgrade_path = os.path.join(base_path, 'base', 'maintenance', 'migrations')
    for up in (tools.config['upgrade_path'] or legacy_upgrade_path).split(','):
        up = os.path.normcase(os.path.abspath(tools.ustr(up.strip())))
        if up not in upgrade.__path__:
            upgrade.__path__.append(up)

    # create decrecated module alias from odoo.addons.base.maintenance.migrations to odoo.upgrade
    spec = importlib.machinery.ModuleSpec("odoo.addons.base.maintenance", None, is_package=True)
    maintenance_pkg = importlib.util.module_from_spec(spec)
    maintenance_pkg.migrations = upgrade
    sys.modules["odoo.addons.base.maintenance"] = maintenance_pkg
    sys.modules["odoo.addons.base.maintenance.migrations"] = upgrade

    if not getattr(initialize_sys_path, 'called', False): # only initialize once
        sys.meta_path.insert(0, OdooHook())
        sys.meta_path.insert(0, AddonsHook())
        initialize_sys_path.called = True


def get_module_path(module, downloaded=False, display_warning=True):
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    initialize_sys_path()
    for adp in odoo.addons.__path__:
        files = [opj(adp, module, manifest) for manifest in MANIFEST_NAMES] +\
                [opj(adp, module + '.zip')]
        if any(os.path.exists(f) for f in files):
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

    files = odoo.tools.osutil.listdir(path, True)

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
    for adpath in odoo.addons.__path__:
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

def module_manifest(path):
    """Returns path to module manifest if one can be found under `path`, else `None`."""
    if not path:
        return None
    for manifest_name in MANIFEST_NAMES:
        if os.path.isfile(opj(path, manifest_name)):
            return opj(path, manifest_name)

def get_module_root(path):
    """
    Get closest module's root beginning from path

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
    while not module_manifest(path):
        new_path = os.path.abspath(opj(path, os.pardir))
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
        mod_path = get_module_path(module, downloaded=True)
    manifest_file = module_manifest(mod_path)
    if manifest_file:
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
            'sequence': 100,
            'summary': '',
            'website': '',
        }
        info.update(zip(
            'depends data demo test init_xml update_xml demo_xml'.split(),
            iter(list, None)))

        f = tools.file_open(manifest_file, mode='rb')
        try:
            info.update(ast.literal_eval(pycompat.to_text(f.read())))
        finally:
            f.close()

        if not info.get('description'):
            readme_path = [opj(mod_path, x) for x in README
                           if os.path.isfile(opj(mod_path, x))]
            if readme_path:
                with tools.file_open(readme_path[0]) as fd:
                    info['description'] = fd.read()

        # auto_install is set to `False` if disabled, and a set of
        # auto_install dependencies otherwise. That way, we can set
        # auto_install: [] to always auto_install a module regardless of its
        # dependencies
        auto_install = info.get('auto_install', info.get('active', False))
        if isinstance(auto_install, collections.Iterable):
            info['auto_install'] = set(auto_install)
            non_dependencies = info['auto_install'].difference(info['depends'])
            assert not non_dependencies,\
                "auto_install triggers must be dependencies, found " \
                "non-dependencies [%s] for module %s" % (
                    ', '.join(non_dependencies), module
                )
        elif auto_install:
            info['auto_install'] = set(info['depends'])
        else:
            info['auto_install'] = False

        info['version'] = adapt_version(info['version'])
        return info

    _logger.debug('module %s: no manifest file found %s', module, MANIFEST_NAMES)
    return {}

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
        __import__('odoo.addons.' + module_name)

        # Call the module's post-load hook. This can done before any model or
        # data has been initialized. This is ok as the post-load hook is for
        # server-wide (instead of registry-specific) functionalities.
        info = load_information_from_description_file(module_name)
        if info['post_load']:
            getattr(sys.modules['odoo.addons.' + module_name], info['post_load'])()

    except Exception as e:
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
            for mname in MANIFEST_NAMES:
                if os.path.isfile(opj(dir, name, mname)):
                    return True
        return [
            clean(it)
            for it in os.listdir(dir)
            if is_really_module(it)
        ]

    plist = []
    initialize_sys_path()
    for ad in odoo.addons.__path__:
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
    results = _get_tests_modules('odoo.addons', module)

    try:
        importlib.import_module('odoo.upgrade.%s' % module)
    except ImportError:
        pass
    else:
        results += _get_tests_modules('odoo.upgrade', module)

    return results

def _get_tests_modules(path, module):
    modpath = '%s.%s' % (path, module)
    try:
        mod = importlib.import_module('.tests', modpath)
    except ImportError as e:  # will also catch subclass ModuleNotFoundError of P3.6
        # Hide ImportErrors on `tests` sub-module, but display other exceptions
        if e.name == modpath + '.tests' and e.msg.startswith('No module named'):
            return []
        _logger.exception('Can not `import %s`.', module)
        return []
    except Exception as e:
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


class OdooTestResult(unittest.result.TestResult):
    """
    This class in inspired from TextTestResult (https://github.com/python/cpython/blob/master/Lib/unittest/runner.py)
    Instead of using a stream, we are using the logger,
    but replacing the "findCaller" in order to give the information we
    have based on the test object that is running.
    """

    def log(self, level, msg, *args, test=None, exc_info=None, extra=None, stack_info=False, caller_infos=None):
        """
        ``test`` is the running test case, ``caller_infos`` is
        (fn, lno, func, sinfo) (logger.findCaller format), see logger.log for
        the other parameters.
        """
        logger = logging.getLogger((test or self).__module__)  # test should be always set
        try:
            caller_infos = caller_infos or logger.findCaller(stack_info)
        except ValueError:
            caller_infos = "(unknown file)", 0, "(unknown function)", None
        (fn, lno, func, sinfo) = caller_infos
        # using logger.log makes it difficult to spot-replace findCaller in
        # order to provide useful location information (the problematic spot
        # inside the test function), so use lower-level functions instead
        if logger.isEnabledFor(level):
            record = logger.makeRecord(logger.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
            logger.handle(record)

    def getDescription(self, test):
        if isinstance(test, unittest.TestCase):
            # since we have the module name in the logger, this will avoid to duplicate module info in log line
            # we only apply this for TestCase since we can receive error handler or other special case
            return "%s.%s" % (test.__class__.__qualname__, test._testMethodName)
        return str(test)

    def startTest(self, test):
        super().startTest(test)
        self.log(logging.INFO, 'Starting %s ...', self.getDescription(test), test=test)

    def addError(self, test, err):
        super().addError(test, err)
        self.logError("ERROR", test, err)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.logError("FAIL", test, err)

    def addSubTest(self, test, subtest, err):
        # since addSubTest is not making a call to addFailure or addError we need to manage it too
        # https://github.com/python/cpython/blob/3.7/Lib/unittest/result.py#L136
        if err is not None:
            if issubclass(err[0], test.failureException):
                flavour = "FAIL"
            else:
                flavour = "ERROR"
            self.logError(flavour, subtest, err)
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.log(logging.INFO, 'skipped %s', self.getDescription(test), test=test)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.log(logging.ERROR, 'unexpected success for %s', self.getDescription(test), test=test)

    def logError(self, flavour, test, error):
        err = self._exc_info_to_string(error, test)
        caller_infos = self.getErrorCallerInfo(error, test)
        self.log(logging.INFO, '=' * 70, test=test, caller_infos=caller_infos)  # keep this as info !!!!!!
        self.log(logging.ERROR, "%s: %s\n%s", flavour, self.getDescription(test), err, test=test, caller_infos=caller_infos)

    def getErrorCallerInfo(self, error, test):
        """
        :param error: A tuple (exctype, value, tb) as returned by sys.exc_info().
        :param test: A TestCase that created this error.
        :returns: a tuple (fn, lno, func, sinfo) matching the logger findCaller format or None
        """

        # only test case should be executed in odoo, this is only a safe guard
        if isinstance(test, unittest.suite._ErrorHolder):
            return
        if not isinstance(test, unittest.TestCase):
            _logger.warning('%r is not a TestCase' % test)
            return
        _, _, error_traceback = error

        while error_traceback:
            code = error_traceback.tb_frame.f_code
            if code.co_name == test._testMethodName:
                lineno = error_traceback.tb_lineno
                filename = code.co_filename
                method = test._testMethodName
                infos = (filename, lineno, method, None)
                return infos
            error_traceback = error_traceback.tb_next


class OdooTestRunner(object):
    """A test runner class that displays results in in logger.
    Simplified verison of TextTestRunner(
    """

    def run(self, test):
        result = OdooTestResult()

        start_time = time.perf_counter()
        test(result)
        time_taken = time.perf_counter() - start_time
        run = result.testsRun
        _logger.info("Ran %d test%s in %.3fs", run, run != 1 and "s" or "", time_taken)
        return result

current_test = None

def run_unit_tests(module_name, position='at_install'):
    """
    :returns: ``True`` if all of ``module_name``'s tests succeeded, ``False``
              if any of them failed.
    :rtype: bool
    """
    global current_test
    from odoo.tests.common import TagsSelector # Avoid import loop
    current_test = module_name
    mods = get_test_modules(module_name)
    threading.currentThread().testing = True
    config_tags = TagsSelector(tools.config['test_tags'])
    position_tag = TagsSelector(position)
    r = True
    for m in mods:
        tests = unwrap_suite(unittest.TestLoader().loadTestsFromModule(m))
        suite = unittest.TestSuite(t for t in tests if position_tag.check(t) and config_tags.check(t))

        if suite.countTestCases():
            t0 = time.time()
            t0_sql = odoo.sql_db.sql_counter
            _logger.info('%s running tests.', m.__name__)
            result = OdooTestRunner().run(suite)
            if time.time() - t0 > 5:
                _logger.log(25, "%s tested in %.2fs, %s queries", m.__name__, time.time() - t0, odoo.sql_db.sql_counter - t0_sql)
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
            unwrap_suite(t) for t in subtests):
        yield item
