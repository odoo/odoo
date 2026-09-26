# Check __all__, __implements__, __extensions__, __imports__ of the modules

from __future__ import print_function
from __future__ import absolute_import


import functools
import sys
import unittest
import types
import importlib
import warnings

from gevent.testing import six
from gevent.testing import modules
from gevent.testing.sysinfo import PLATFORM_SPECIFIC_SUFFIXES
from gevent.testing.util import debug

from gevent._patcher import MAPPING

class ANY(object):
    def __contains__(self, item):
        return True

ANY = ANY()

NOT_IMPLEMENTED = {
    'socket': ['CAPI'],
    'thread': ['allocate', 'exit_thread', 'interrupt_main', 'start_new'],
    'select': ANY,
    'os': ANY,
    'threading': ANY,
    '__builtin__' if six.PY2 else 'builtins': ANY,
    'signal': ANY,
}

COULD_BE_MISSING = {
    'socket': ['create_connection', 'RAND_add', 'RAND_egd', 'RAND_status'],
    'subprocess': ['_posixsubprocess'],
}

# Things without an __all__ should generally be internal implementation
# helpers
NO_ALL = {
    'gevent.threading',
    'gevent._compat',
    'gevent._corecffi',
    'gevent._ffi',
    'gevent._fileobjectcommon',
    'gevent._fileobjectposix',
    'gevent._patcher',
    'gevent._socketcommon',
    'gevent._tblib',
    'gevent._util',
    'gevent.resolver._addresses',
    'gevent.resolver._hostsfile',
}

ALLOW_IMPLEMENTS = [
    'gevent._queue',
    # 'gevent.resolver.dnspython',
    # 'gevent.resolver_thread',
    # 'gevent.resolver.blocking',
    # 'gevent.resolver_ares',
    # 'gevent.server',
    # 'gevent._resolver.hostfile',
    # 'gevent.util',
    # 'gevent.threadpool',
    # 'gevent.timeout',
]

# A list of modules that may contain things that aren't actually, technically,
# extensions, but that need to be in __extensions__ anyway due to the way,
# for example, monkey patching, needs to work.
EXTRA_EXTENSIONS = []
if sys.platform.startswith('win'):
    EXTRA_EXTENSIONS.append('gevent.signal')



_MISSING = '<marker object>'

def skip_if_no_stdlib_counterpart(f):
    @functools.wraps(f)
    def m(self):
        if not self.stdlib_module:
            self.skipTest("Need stdlib counterpart to %s" % self.modname)
        f(self)

    return m

class AbstractTestMixin(object):
    modname = None
    stdlib_has_all = False
    stdlib_all = None
    stdlib_name = None
    stdlib_module = None

    @classmethod
    def setUpClass(cls):
        modname = cls.modname
        if modname.endswith(PLATFORM_SPECIFIC_SUFFIXES):
            raise unittest.SkipTest("Module %s is platform specific" % modname)


        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            try:
                cls.module = importlib.import_module(modname)
            except ImportError:
                if modname in modules.OPTIONAL_MODULES:
                    msg = "Unable to import %s" % modname
                    raise unittest.SkipTest(msg)
                raise

        cls.__implements__ = getattr(cls.module, '__implements__', None)
        cls.__imports__ = getattr(cls.module, '__imports__', [])
        cls.__extensions__ = getattr(cls.module, '__extensions__', [])

        cls.stdlib_name = MAPPING.get(modname)

        if cls.stdlib_name is not None:
            try:
                cls.stdlib_module = __import__(cls.stdlib_name)
            except ImportError:
                pass
            else:
                cls.stdlib_has_all = True
                cls.stdlib_all = getattr(cls.stdlib_module, '__all__', None)
                if cls.stdlib_all is None:
                    cls.stdlib_has_all = False
                    cls.stdlib_all = [
                        name
                        for name in dir(cls.stdlib_module)
                        if not name.startswith('_')
                        and not isinstance(getattr(cls.stdlib_module, name), types.ModuleType)
                    ]

    def skipIfNoAll(self):
        if not hasattr(self.module, '__all__'):
            self.assertIn(self.modname, NO_ALL)
            self.skipTest("%s Needs __all__" % self.modname)

    def test_all(self):
        # Check that __all__ is present in the gevent module,
        # and only includes things that actually exist and can be
        # imported from it.
        self.skipIfNoAll()
        names = {}
        six.exec_("from %s import *" % self.modname, names)
        names.pop('__builtins__', None)
        self.maxDiff = None

        # It should match both as a set
        self.assertEqual(set(names), set(self.module.__all__))
        # and it should not contain duplicates.
        self.assertEqual(sorted(names), sorted(self.module.__all__))

    def test_all_formula(self):
        self.skipIfNoAll()
        # Check __all__ = __implements__ + __extensions__ + __imported__
        # This is disabled because it was previously being skipped entirely
        # back when we had to call things manually. In that time, it drifted
        # out of sync. It should be enabled again and problems corrected.
        all_calculated = (
            tuple(self.__implements__ or ())
            + tuple(self.__imports__  or ())
            + tuple(self.__extensions__ or ())
        )
        try:
            self.assertEqual(sorted(all_calculated),
                             sorted(self.module.__all__))
        except AssertionError:
            self.skipTest("Module %s fails the all formula; fix it" % self.modname)

    def test_implements_presence_justified(self):
        # Check that __implements__ is present only if the module is modeled
        # after a module from stdlib (like gevent.socket).

        if self.modname in ALLOW_IMPLEMENTS:
            return
        if self.__implements__ is not None and self.stdlib_module is None:
            raise AssertionError(
                '%s (%r) has __implements__ (%s) but no stdlib counterpart module exists (%s)'
                % (self.modname, self.module, self.__implements__, self.stdlib_name))

    @skip_if_no_stdlib_counterpart
    def test_implements_subset_of_stdlib_all(self):
        # Check that __implements__ + __imports__ is a subset of the
        # corresponding standard module __all__ or dir()
        for name in tuple(self.__implements__ or ()) + tuple(self.__imports__):
            if name in self.stdlib_all:
                continue
            if name in COULD_BE_MISSING.get(self.stdlib_name, ()):
                continue
            if name in dir(self.stdlib_module):  # like thread._local which is not in thread.__all__
                continue
            raise AssertionError('%r is not found in %r.__all__ nor in dir(%r)' % (name, self.stdlib_module, self.stdlib_module))

    @skip_if_no_stdlib_counterpart
    def test_implements_actually_implements(self):
        # Check that the module actually implements the entries from
        # __implements__

        for name in self.__implements__ or ():
            item = getattr(self.module, name)
            try:
                stdlib_item = getattr(self.stdlib_module, name)
                self.assertIsNot(item, stdlib_item)
            except AttributeError:
                if name not in COULD_BE_MISSING.get(self.stdlib_name, []):
                    raise

    @skip_if_no_stdlib_counterpart
    def test_imports_actually_imports(self):
        # Check that the module actually imports the entries from
        # __imports__
        for name in self.__imports__:
            item = getattr(self.module, name)
            stdlib_item = getattr(self.stdlib_module, name)
            self.assertIs(item, stdlib_item)

    @skip_if_no_stdlib_counterpart
    def test_extensions_actually_extend(self):
        # Check that the module actually defines new entries in
        # __extensions__

        if self.modname in EXTRA_EXTENSIONS:
            return
        for name in self.__extensions__:
            if hasattr(self.stdlib_module, name):
                raise AssertionError("'%r' is not an extension, it is found in %r" % (name, self.stdlib_module))

    @skip_if_no_stdlib_counterpart
    def test_completeness(self): # pylint:disable=too-many-branches
        # Check that __all__ (or dir()) of the corresponsing stdlib is
        # a subset of __all__ of this module

        missed = []
        for name in self.stdlib_all:
            if name not in getattr(self.module, '__all__', []):
                missed.append(name)

        # handle stuff like ssl.socket and ssl.socket_error which have no reason to be in gevent.ssl.__all__
        if not self.stdlib_has_all:
            for name in missed[:]:
                if hasattr(self.module, name):
                    missed.remove(name)

        # remove known misses
        not_implemented = NOT_IMPLEMENTED.get(self.stdlib_name)
        if not_implemented is not None:
            result = []
            for name in missed:
                if name in not_implemented:
                    # We often don't want __all__ to be set because we wind up
                    # documenting things that we just copy in from the stdlib.
                    # But if we implement it, don't print a warning
                    if getattr(self.module, name, _MISSING) is _MISSING:
                        debug('IncompleteImplWarning: %s.%s' % (self.modname, name))
                else:
                    result.append(name)
            missed = result

        if missed:
            if self.stdlib_has_all:
                msg = '''The following items
              in %r.__all__
are missing from %r:
                 %r''' % (self.stdlib_module, self.module, missed)
            else:
                msg = '''The following items
          in dir(%r)
are missing from %r:
                 %r''' % (self.stdlib_module, self.module, missed)
            raise AssertionError(msg)


def _create_tests():
    for _, modname in modules.walk_modules(include_so=False, recursive=True,
                                           check_optional=False):
        if modname.endswith(PLATFORM_SPECIFIC_SUFFIXES):
            continue

        orig_modname = modname
        modname_no_period = orig_modname.replace('.', '_')

        cls = type(
            'Test_' + modname_no_period,
            (AbstractTestMixin, unittest.TestCase),
            {
                '__module__': __name__,
                'modname': orig_modname
            }
        )
        globals()[cls.__name__] = cls

_create_tests()

if __name__ == "__main__":
    unittest.main()
