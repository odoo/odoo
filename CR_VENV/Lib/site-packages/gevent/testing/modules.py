# Copyright (c) 2018 gevent community
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import absolute_import, print_function, division

import importlib
import os.path
import warnings

import gevent

from . import sysinfo
from . import util


OPTIONAL_MODULES = frozenset({
    ## Resolvers.
    # ares might not be built
    'gevent.resolver_ares',
    'gevent.resolver.ares',
    # dnspython might not be installed
    'gevent.resolver.dnspython',
    ## Backends
    'gevent.libev',
    'gevent.libev.watcher',
    'gevent.libuv.loop',
    'gevent.libuv.watcher',
})

EXCLUDED_MODULES = frozenset({
    '__init__',
    'core',
    'ares',
    '_util',
    '_semaphore',
    'corecffi',
    '_corecffi',
    '_corecffi_build',
})

def walk_modules(
        basedir=None,
        modpath=None,
        include_so=False,
        recursive=False,
        check_optional=True,
        include_tests=False,
        optional_modules=OPTIONAL_MODULES,
        excluded_modules=EXCLUDED_MODULES,
):
    """
    Find gevent modules, yielding tuples of ``(path, importable_module_name)``.

    :keyword bool check_optional: If true (the default), then if we discover a
       module that is known to be optional on this system (such as a backend),
       we will attempt to import it; if the import fails, it will not be returned.
       If false, then we will not make such an attempt, the caller will need to be prepared
       for an `ImportError`; the caller can examine *optional_modules* against
       the yielded *importable_module_name*.
    """
    # pylint:disable=too-many-branches
    if sysinfo.PYPY:
        include_so = False
    if basedir is None:
        basedir = os.path.dirname(gevent.__file__)
        if modpath is None:
            modpath = 'gevent.'
    else:
        if modpath is None:
            modpath = ''

    for fn in sorted(os.listdir(basedir)):
        path = os.path.join(basedir, fn)
        if os.path.isdir(path):
            if not recursive:
                continue
            if not include_tests and fn in ['testing', 'tests']:
                continue
            pkg_init = os.path.join(path, '__init__.py')
            if os.path.exists(pkg_init):
                yield pkg_init, modpath + fn
                for p, m in walk_modules(
                        path, modpath + fn + ".",
                        include_so=include_so,
                        recursive=recursive,
                        check_optional=check_optional,
                        include_tests=include_tests,
                        optional_modules=optional_modules,
                        excluded_modules=excluded_modules,
                ):
                    yield p, m
            continue

        if fn.endswith('.py'):
            x = fn[:-3]
            if x.endswith('_d'):
                x = x[:-2]
            if x in excluded_modules:
                continue
            modname = modpath + x
            if check_optional and modname in optional_modules:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', DeprecationWarning)
                        importlib.import_module(modname)
                except ImportError:
                    util.debug("Unable to import optional module %s", modname)
                    continue
            yield path, modname
        elif include_so and fn.endswith(sysinfo.SHARED_OBJECT_EXTENSION):
            if '.pypy-' in fn:
                continue
            if fn.endswith('_d.so'):
                yield path, modpath + fn[:-5]
            else:
                yield path, modpath + fn[:-3]
