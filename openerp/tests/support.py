# -*- coding: utf-8 -*-
"""
Support types and functions bridging pytest's test runner and odoo to allow
running tests at all.

Supports both the CLI test runner (odoo.py test) and the "inline" test runner
(odoo.py server --test-enable)
"""
import collections
import contextlib
import itertools
import logging
import os
import sys
import threading

import py.error
import py.code
import traceback
import _pytest.python
import pytest

from openerp.modules import module, graph
from openerp import tools

_test_logger = logging.getLogger('openerp.tests')


class TestReporter(object):
    def __init__(self):
        self.tests = 0
        self.successes = 0
        self.skipped = []
        self.failures = []
    def pytest_collectreport(self, report):
        if report.failed:
            self.failures.append(report)
        elif report.skipped:
            self.skipped.append(report)

    def pytest_runtest_logreport(self, report):
        testpath = getattr(report, 'nodeid', '')
        logger = _test_logger.getChild('test')

        if report.passed:
            if report.when != 'call':
                return
            self.successes += 1
            logger.info("%s %s %s", 'pass', testpath, report.longrepr or '')
        elif report.skipped:
            self.skipped.append(report)
            # maybe should be logged as a warning?
            logger.info("%s %s %s", 'skip', testpath, report.longrepr[2])
        elif report.failed:
            self.failures.append(report)
            logger.error("%s %s %s", 'fail', testpath, report.longrepr)
        self.tests += 1

    def log_results(self):
        _test_logger.info(
            "%d tests, %d successes, %d skipped, %d failed",
            self.tests, self.successes, len(self.skipped), len(self.failures))
        if self.failures:
            _test_logger.error("%d failure(s) while loading modules", len(self.failures))

        for skipped in self.skipped:
            _test_logger.debug(
                "%s %s",
                getattr(skipped, 'nodeid', None) or skipped.fspath,
                skipped.longrepr[2]
            )
        for failure in self.failures:
            _test_logger.error(
                "%s %s",
                getattr(failure, 'nodeid', None) or failure.fspath,
                failure.longrepr
            )


class OdooTestModule(_pytest.python.Module):
    """ Should only be invoked for paths inside Odoo addons, overrides module
    name for Odoo modules so they're imported via e.g. openerp.addons.sale
    rather than just sale, otherwise the import may fail and if it does not
    it's going to a second completely different import of the module and
    everything's going to end up weird.
    """
    def _importtestmodule(self):
        # copy/paste/modified from original: removed sys.path injection &
        # added Odoo module prefixing so import within modules is correct
        try:
            pypkgpath = self.fspath.pypkgpath()
            pkgroot = pypkgpath.dirpath()
            names = self.fspath.new(ext="").relto(pkgroot).split(self.fspath.sep)
            if names[-1] == "__init__":
                names.pop()
            modname = ".".join(names)
            # for modules in openerp/addons, since there is a __init__ the
            # module name is already fully qualified (maybe?)
            if not modname.startswith('openerp.addons.'):
                modname = 'openerp.addons.' + modname

            __import__(modname)
            mod = sys.modules[modname]
            if self.fspath.basename == "__init__.py":
                return mod # we don't check anything as we might
                           # we in a namespace package ... too icky to check
            modfile = mod.__file__
            if modfile[-4:] in ('.pyc', '.pyo'):
                modfile = modfile[:-1]
            elif modfile.endswith('$py.class'):
                modfile = modfile[:-9] + '.py'
            if modfile.endswith(os.path.sep + "__init__.py"):
                if self.fspath.basename != "__init__.py":
                    modfile = modfile[:-12]
            try:
                issame = self.fspath.samefile(modfile)
            except py.error.ENOENT:
                issame = False
            if not issame:
                raise self.fspath.ImportMismatchError(modname, modfile, self)
        except SyntaxError:
            raise self.CollectError(
                py.code.ExceptionInfo().getrepr(style="short"))
        except self.fspath.ImportMismatchError:
            e = sys.exc_info()[1]
            raise self.CollectError(
                "import file mismatch:\n"
                "imported module %r has this __file__ attribute:\n"
                "  %s\n"
                "which is not the same as the test file we want to collect:\n"
                "  %s\n"
                "HINT: remove __pycache__ / .pyc files and/or use a "
                "unique basename for your test file modules"
                 % e.args
            )
        #print "imported test module", mod
        self.config.pluginmanager.consider_module(mod)
        return mod


class ModuleTest(object):
    """ Performs filtering for inline test run: restricts tests collected
    to those with the specified at_install/post_install phase
    """
    defaults = {
        'at_install': True,
        'post_install': False
    }
    def __init__(self, phase):
        self.phase = phase

    def pytest_collection_modifyitems(self, session, config, items):
        items[:] = filter(self._filter_phase, items)

    def _filter_phase(self, item):
        marker = item.get_marker(self.phase)
        if marker and marker.args:
            return marker.args[0]
        return self.defaults[self.phase]

    @pytest.mark.tryfirst
    def pytest_pycollect_makemodule(self, path, parent):
        """ override collect with own test module thing to alter generated
        module name when tests are found within an Odoo module: rather than
        import ``<module>.foo.bar`` it should be
        ``openerp.addons.<module>.foo.bar``
        """
        # if path to collect is in addons_path, create an OdooTestModule
        p = str(path) # work with strings because cheap. TODO: check that it works on windows
        if any(p.startswith(root) for root in module.ad_paths):
            return OdooTestModule(path, parent)
        # otherwise create a normal test module
        return None


class DataTests(object):
    """
    pytest plugin implementing "data" tests (XML and YAML test files specified
    via the ``test`` key of the manifest).

    Generates tests based on the manifest file itself, each manifest generates
    a single test as all test files must be executed in-order in the same
    transaction.

    See http://pytest-c-testrunner.readthedocs.org/ for a basic tutorial on
    custom/non-python tests in pytest, which is part of the inspiration for
    this stuff
    """
    def __init__(self, registry, package):
        self.package = package
        self.registry = registry
    def pytest_collect_file(self, parent, path):
        if path.basename != '__openerp__.py':
            return

        testfiles = [module.get_resource_path(self.package.name, p) for p in
                    self.registry._get_files_of_kind('test', self.package)]
        if not testfiles:
            return

        return DataFile(path, parent, self.registry, self.package, testfiles)
class DataFile(pytest.File):
    def __init__(self, path, parent, registry, package, paths):
        super(DataFile, self).__init__(path, parent)
        self.registry = registry
        self.package = package
        self.paths = paths
    def collect(self):
        return [DataItem(self, self.registry, self.package, self.paths)]
class DataItem(pytest.Item):
    def __init__(self, parent, registry, package, paths):
        super(DataItem, self).__init__(package.name, parent)
        self.package = package
        self.registry = registry
        self.paths = paths
        self.current = None

    def runtest(self):
        mode = 'update'
        if hasattr(self.package, 'init') or self.package.state == 'to_install':
            mode = 'init'

        try:
            threading.currentThread().testing = True
            with contextlib.closing(self.registry.cursor()) as cr:
                idrefs = {}
                for p in self.paths:
                    self.current = p
                    tools.convert_file(
                        cr, self.package.name, p, idrefs, mode=mode,
                        noupdate=False, kind='test', pathname=p)
        finally:
            self.registry.clear_caches()
            threading.currentThread().testing = False

    def reportinfo(self):
        return self.fspath, 0, ""

    def repr_failure(self, exc_info):
        return "Test failed in %s\n%s" % (self.current, ''.join(traceback.format_exception(*exc_info._excinfo)))

def is_at_install(item):
    marker = item.get_marker('at_install')
    return marker.args[0] if marker and marker.args else True
def is_post_install(item):
    marker = item.get_marker('post_install')
    return marker.args[0] if marker and marker.args else False
Package = collections.namedtuple('Package', 'name init state')
class OdooTests(object):
    """
    Primary plugin for the test subcommand, currently requires a brand new
    registry added to the RegistryManager, and running with a locked
    RegistryManager and the environments being setup.
    """
    def __init__(self, registry):
        self.registry = registry
        self.processed = set()
        # stream of module loading thing, replaced by None to indicate that
        # installation process is done, should do nothing until the first
        # next() call so it's safe to create it immediately
        self.loader_stream = registry.load_modules(force_demo=True)

    def pytest_collect_file(self, parent, path):
        """
        Add collection of "data test" files as a single case each

        Same purpose as and partially redundant with DataTests, it may be nice
        to unify them eventually
        """
        if path.basename != '__openerp__.py':
            return
        mod = path.dirpath().basename
        info = module.load_information_from_description_file(mod)
        if not (info.get('installable', True) and info.get('test')):
            return

        return DataFile(
            path, parent, self.registry,
            Package(name=mod, state='to install', init=True),
            [str(path.dirpath(data)) for data in info.get('test')]
        )

    def pytest_collection_modifyitems(self, session, config, items):
        # setup modules to install after we've collected all items so we know
        # exactly what will be required
        path_and_mod = ((str(item.fspath), module.get_resource_from_path(str(item.fspath))) for item in items)
        path_to_mod = {path: res[0] for (path, res) in path_and_mod if res}
        to_load = set(path_to_mod.itervalues())

        to_install = collections.defaultdict(lambda: True)
        with contextlib.closing(self.registry.cursor()) as cr:
            cr.execute("SELECT relname FROM pg_class WHERE relname='ir_module_module'")
            if cr.fetchone():
                # ir_module_module already exists, we might be in an update
                # situation, don't assume every module should be installed
                cr.execute("SELECT name, state NOT IN ('installed', 'to upgrade', 'to remove')"
                           " FROM ir_module_module")
                to_install = dict(cr.fetchall())

        # demo lists all explicitly specified modules
        tools.config['demo'] = dict.fromkeys(to_load, 1)
        # init lists the explicitly specified modules to install
        tools.config['init'] = {mod: 1 for mod in to_load if to_install[mod]}
        # update lists explicitly specified modules to update
        tools.config['update'] = {mod: 1 for mod in to_load if not to_install[mod]}
        # FIXME: this is disgusting
        tools.config['test_enable'] = True

        g = graph.Graph()
        # disable update_from_db we should not need it and ir_module_module
        # is not loaded yet so it blows up
        g.update_from_db = lambda cr: 0
        with contextlib.closing(self.registry.cursor()) as cr:
            g.add_modules(cr, ['base'])
            # module_name: sequence
            mods = {}
            # we need to add explicitly requested modules *and their
            # dependencies* to the graph
            while to_load:
                mod = to_load.pop()
                info = module.load_information_from_description_file(mod)
                mods[mod] = info.get('sequence', 100)
                to_load.update(dep for dep in info['depends'] if dep not in mods)
            # don't reload base after having loaded it explicitly
            mods.pop('base', None)
            # ir_module_module not loaded yet but load_marked_modules gets
            # mods in "natural" table order which is (sequence, name). The
            # sequence is fetched from the terp file. Try to replicate in
            # order to load the graph in the right order. Prefix with whether
            # the module is already installed or not: installed module (to
            # update?) should be loaded first
            g.add_modules(cr, sorted(mods, key=lambda m: (to_install[m], mods[m], m)))

        c = itertools.count()
        order = {node.name: next(c) for node in g}
        def sort_item_by_load_order(item):
            mod = path_to_mod.get(str(item.fspath))
            if mod is None:
                # start with items not in modules
                return -1
            return to_install[mod], order[mod]

        items.sort(key=sort_item_by_load_order)

        items[:] = filter(is_at_install, items) + filter(is_post_install, items)

    def pytest_runtest_protocol(self, item, nextitem):
        res = module.get_resource_from_path(str(item.fspath))
        if res is None:
            # not a module, let test behave normally
            return
        # ensure module has been processed (installed)
        (modname, _, _) = res
        while self.loader_stream and modname not in self.processed:
            try:
                event, package = next(self.loader_stream)
            except StopIteration:
                break
            if event == 'module_processed':
                self.processed.add(package.name)

            ir_http = self.registry['ir.http']
            if hasattr(ir_http, '_routing_map'):
                # Force routing map to be rebuilt between each module test suite
                del ir_http._routing_map

            module.current_test = package.name

        if self.loader_stream and is_post_install(item):
            self.finalize_stream()

    def pytest_sessionfinish(self):
        # if there's no post_install tests we need to finalize the stream
        # at some point or the final installed module will not be correctly
        # marked and auto_install dependents may not be installed at all.
        if self.loader_stream:
            self.finalize_stream()

    def finalize_stream(self):
        # ensure loader_stream is exhausted and finalised
        for _ in self.loader_stream: pass
        self.loader_stream = None
        module.current_test = None

    @pytest.mark.tryfirst
    def pytest_pycollect_makemodule(self, path, parent):
        """ If the path is with an Odoo module, return a special module which
        fixups the base import by prefixing the module name with
        `openerp.addons.
        """
        if module.get_resource_from_path(str(path)):
            return OdooTestModule(path, parent)
        return None
