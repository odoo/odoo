from __future__ import print_function

import doctest
import functools
import os
import re
import sys
import unittest



# Ignore tracebacks: ZeroDivisionError


def myfunction(*_args, **_kwargs):
    pass


class RENormalizingOutputChecker(doctest.OutputChecker):
    """
    Pattern-normalizing output checker. Inspired by one used in zope.testing.
    """

    def __init__(self, patterns):
        self.transformers = [functools.partial(re.sub, replacement) for re, replacement in patterns]

    def check_output(self, want, got, optionflags):
        if got == want:
            return True

        for transformer in self.transformers:
            want = transformer(want)
            got = transformer(got)

        return doctest.OutputChecker.check_output(self, want, got, optionflags)

FORBIDDEN_MODULES = set()


class Modules(object):

    def __init__(self, allowed_modules):
        from gevent.testing import walk_modules
        self.allowed_modules = allowed_modules
        self.modules = set()

        for path, module in walk_modules(recursive=True):
            self.add_module(module, path)


    def add_module(self, name, path):
        if self.allowed_modules and name not in self.allowed_modules:
            return
        if name in FORBIDDEN_MODULES:
            return
        self.modules.add((name, path))

    def __bool__(self):
        return bool(self.modules)

    __nonzero__ = __bool__

    def __iter__(self):
        return iter(self.modules)


def main(): # pylint:disable=too-many-locals
    cwd = os.getcwd()
    # Use pure_python to get the correct module source and docstrings
    os.environ['PURE_PYTHON'] = '1'

    import gevent
    from gevent import socket


    from gevent.testing import util
    from gevent.testing import sysinfo

    if sysinfo.WIN:
        FORBIDDEN_MODULES.update({
            # Uses commands only found on posix
            'gevent.subprocess',
        })

    try:
        allowed_modules = sys.argv[1:]
        sys.path.append('.')

        globs = {
            'myfunction': myfunction,
            'gevent': gevent,
            'socket': socket,
        }

        modules = Modules(allowed_modules)

        if not modules:
            sys.exit('No modules found matching %s' % ' '.join(allowed_modules))

        suite = unittest.TestSuite()
        checker = RENormalizingOutputChecker((
            # Normalize subprocess.py: BSD ls is in the example, gnu ls outputs
            # 'cannot access'
            (re.compile(
                "ls: cannot access 'non_existent_file': No such file or directory"),
             "ls: non_existent_file: No such file or directory"),
            # Python 3 bytes add a "b".
            (re.compile(r'b(".*?")'), r"\1"),
            (re.compile(r"b('.*?')"), r"\1"),
        ))

        tests_count = 0
        modules_count = 0
        for m, path in sorted(modules):
            with open(path, 'rb') as f:
                contents = f.read()
            if re.search(br'^\s*>>> ', contents, re.M):
                s = doctest.DocTestSuite(m, extraglobs=globs, checker=checker)
                test_count = len(s._tests)
                util.log('%s (from %s): %s tests', m, path, test_count)
                suite.addTest(s)
                modules_count += 1
                tests_count += test_count

        util.log('Total: %s tests in %s modules', tests_count, modules_count)
        # TODO: Pass this off to unittest.main()
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    finally:
        os.chdir(cwd)

if __name__ == '__main__':
    main()
