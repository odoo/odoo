# Copyright 2018 gevent. See LICENSE for details.

# Portions of the following are inspired by code from eventlet. I
# believe they are distinct enough that no eventlet copyright would
# apply (they are not a copy or substantial portion of the eventlot
# code).

# Added in gevent 1.3a2. Not public in that release.

from __future__ import absolute_import, print_function

import importlib
import sys


from gevent._compat import iteritems
from gevent._compat import imp_acquire_lock
from gevent._compat import imp_release_lock


from gevent.builtins import __import__ as g_import


MAPPING = {
    'gevent.local': '_threading_local',
    'gevent.socket': 'socket',
    'gevent.select': 'select',
    'gevent.selectors': 'selectors',
    'gevent.ssl': 'ssl',
    'gevent.thread': '_thread',
    'gevent.subprocess': 'subprocess',
    'gevent.os': 'os',
    'gevent.threading': 'threading',
    'gevent.builtins': 'builtins',
    'gevent.signal': 'signal',
    'gevent.time': 'time',
    'gevent.queue': 'queue',
    'gevent.contextvars': 'contextvars',
}

OPTIONAL_STDLIB_MODULES = frozenset()
_PATCH_PREFIX = '__g_patched_module_'

def _collect_stdlib_gevent_modules():
    """
    Return a map from standard library name to
    imported gevent module that provides the same API.

    Optional modules are skipped if they cannot be imported.
    """
    result = {}

    for gevent_name, stdlib_name in iteritems(MAPPING):
        try:
            result[stdlib_name] = importlib.import_module(gevent_name)
        except ImportError:
            if stdlib_name in OPTIONAL_STDLIB_MODULES:
                continue
            raise
    return result


class _SysModulesPatcher(object):

    def __init__(self, importing, extra_all=lambda mod_name: ()):
        # Permanent state.
        self.extra_all = extra_all
        self.importing = importing
        # green modules, replacing regularly imported modules.
        # This begins as the gevent list of modules, and
        # then gets extended with green things from the tree we import.
        self._green_modules = _collect_stdlib_gevent_modules()

        ## Transient, reset each time we're called.
        # The set of things imported before we began.
        self._t_modules_to_restore = {}

    def _save(self):
        self._t_modules_to_restore = {}

        # Copy all the things we know we are going to overwrite.
        for modname in self._green_modules:
            self._t_modules_to_restore[modname] = sys.modules.get(modname, None)

        # Copy anything else in the import tree.
        for modname, mod in list(iteritems(sys.modules)):
            if modname.startswith(self.importing):
                self._t_modules_to_restore[modname] = mod
                # And remove it. If it had been imported green, it will
                # be put right back. Otherwise, it was imported "manually"
                # outside this process and isn't green.
                del sys.modules[modname]

        # Cover the target modules so that when you import the module it
        # sees only the patched versions
        for name, mod in iteritems(self._green_modules):
            sys.modules[name] = mod

    def _restore(self):
        # Anything from the same package tree we imported this time
        # needs to be saved so we can restore it later, and so it doesn't
        # leak into the namespace.

        for modname, mod in list(iteritems(sys.modules)):
            if modname.startswith(self.importing):
                self._green_modules[modname] = mod
                del sys.modules[modname]

        # Now, what we saved at the beginning needs to be restored.
        for modname, mod in iteritems(self._t_modules_to_restore):
            if mod is not None:
                sys.modules[modname] = mod
            else:
                try:
                    del sys.modules[modname]
                except KeyError:
                    pass

    def __exit__(self, t, v, tb):
        try:
            self._restore()
        finally:
            imp_release_lock()
            self._t_modules_to_restore = None


    def __enter__(self):
        imp_acquire_lock()
        self._save()
        return self

    module = None

    def __call__(self, after_import_hook):
        if self.module is None:
            with self:
                self.module = self.import_one(self.importing, after_import_hook)
                # Circular reference. Someone must keep a reference to this module alive
                # for it to be visible. We record it in sys.modules to be that someone, and
                # to aid debugging. In the past, we worked with multiple completely separate
                # invocations of `import_patched`, but we no longer do.
                self.module.__gevent_patcher__ = self
                sys.modules[_PATCH_PREFIX + self.importing] = self.module
        return self

    def import_one(self, module_name, after_import_hook):
        patched_name = _PATCH_PREFIX + module_name
        if patched_name in sys.modules:
            return sys.modules[patched_name]

        assert module_name.startswith(self.importing)
        sys.modules.pop(module_name, None)

        module = g_import(module_name, {}, {}, module_name.split('.')[:-1])
        self.module = module
        # On Python 3, we could probably do something much nicer with the
        # import machinery? Set the __loader__ or __finder__ or something like that?
        self._import_all([module])
        after_import_hook(module)
        return module

    def _import_all(self, queue):
        # Called while monitoring for patch changes.
        while queue:
            module = queue.pop(0)
            name = module.__name__
            mod_all = tuple(getattr(module, '__all__', ())) + self.extra_all(name)
            for attr_name in mod_all:
                try:
                    getattr(module, attr_name)
                except AttributeError:
                    module_name = module.__name__ + '.' + attr_name
                    new_module = g_import(module_name, {}, {}, attr_name)
                    setattr(module, attr_name, new_module)
                    queue.append(new_module)


def import_patched(module_name,
                   extra_all=lambda mod_name: (),
                   after_import_hook=lambda module: None):
    """
    Import *module_name* with gevent monkey-patches active,
    and return an object holding the greened module as *module*.

    Any sub-modules that were imported by the package are also
    saved.

    .. versionchanged:: 1.5a4
       If the module defines ``__all__``, then each of those
       attributes/modules is also imported as part of the same transaction,
       recursively. The order of ``__all__`` is respected. Anything passed in
       *extra_all* (which must be in the same namespace tree) is also imported.

    .. versionchanged:: 1.5a4
       You must now do all patching for a given module tree
       with one call to this method, or at least by using the returned
       object.
    """

    with cached_platform_architecture():
        # Save the current module state, and restore on exit,
        # capturing desirable changes in the modules package.
        patcher = _SysModulesPatcher(module_name, extra_all)
        patcher(after_import_hook)
    return patcher


class cached_platform_architecture(object):
    """
    Context manager that caches ``platform.architecture``.

    Some things that load shared libraries (like Cryptodome, via
    dnspython) invoke ``platform.architecture()`` for each one. That
    in turn wants to fork and run commands , which in turn wants to
    call ``threading._after_fork`` if the GIL has been initialized.
    All of that means that certain imports done early may wind up
    wanting to have the hub initialized potentially much earlier than
    before.

    Part of the fix is to observe when that happens and delay
    initializing parts of gevent until as late as possible (e.g., we
    delay importing and creating the resolver until the hub needs it,
    unless explicitly configured).

    The rest of the fix is to avoid the ``_after_fork`` issues by
    first caching the results of platform.architecture before doing
    patched imports.

    (See events.py for similar issues with platform, and
    test__threading_2.py for notes about threading._after_fork if the
    GIL has been initialized)
    """

    _arch_result = None
    _orig_arch = None
    _platform = None

    def __enter__(self):
        import platform
        self._platform = platform
        self._arch_result = platform.architecture()
        self._orig_arch = platform.architecture
        def arch(*args, **kwargs):
            if not args and not kwargs:
                return self._arch_result
            return self._orig_arch(*args, **kwargs)
        platform.architecture = arch
        return self

    def __exit__(self, *_args):
        self._platform.architecture = self._orig_arch
        self._platform = None
