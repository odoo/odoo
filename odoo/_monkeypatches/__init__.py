# ruff: noqa: F401, PLC0415
# ignore import not at top of the file
import functools
import importlib
import os
import sys
import time
from types import SimpleNamespace

from .evented import patch_module as patch_evented


def set_timezone_utc():
    os.environ['TZ'] = 'UTC'  # Set the timezone
    if hasattr(time, 'tzset'):
        time.tzset()


class PatchImportHook:
    """Register hooks that are run on import."""

    def __init__(self):
        self.hooks = {}

    def add_hook(self, fullname: str, hook):
        """Register a hook after a module is loaded.
        If already loaded, run hook immediately."""
        self.hooks[fullname] = hook
        if fullname in sys.modules:
            hook()

    def find_spec(self, fullname, path=None, target=None):
        hook = self.hooks.get(fullname)
        if hook is None:
            return  # let python use another import hook to import this fullname

        # skip all finders before this one
        idx = sys.meta_path.index(self)
        for finder in sys.meta_path[idx + 1:]:
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                # we found a spec, change the loader

                def exec_module(module, exec_module=spec.loader.exec_module):
                    res = exec_module(module)
                    hook()
                    return res

                spec.loader = SimpleNamespace(create_module=spec.loader.create_module, exec_module=exec_module)
                return spec
        raise ImportError(f"Could not load the module {fullname!r} to patch")


HOOK_IMPORT = PatchImportHook()
sys.meta_path.insert(0, HOOK_IMPORT)


def patch_init():
    patch_evented()
    set_timezone_utc()

    def patch_module(name):
        """Load and apply monkeypatches.

        For a module name, run the equivalent to::

            from . import {name} as x
            x.patch_{name}()
        """
        module = importlib.import_module(f'.{name}', __name__)
        func = getattr(module, 'patch_module')
        func()

    patch_module('codecs')
    patch_module('win32')
    for name in (
        'ast', 'email', 'mimetypes', 'num2words', 'pytz', 'stdnum', 'urllib3',
        'werkzeug', 'zeep',
    ):
        HOOK_IMPORT.add_hook(name, functools.partial(patch_module, name))
