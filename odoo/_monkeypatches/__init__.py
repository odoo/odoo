"""Lazy module monkeypatcher

Submodules should be named after the module (stdlib or third-party) they need
to patch, and should define a `patch_module` function.

This function will be called either immediately if the module to patch is
already imported when the monkey patcher runs, or right after that module is
imported otherwise.
"""

import importlib
import os
import pkgutil
import sys
import time
from types import ModuleType, SimpleNamespace


class PatchImportHook:
    """Register hooks that are run on import."""

    def __init__(self):
        self.hooks = set()

    def add_hook(self, fullname: str) -> None:
        """Register a hook after a module is loaded.
        If already loaded, run hook immediately."""
        self.hooks.add(fullname)
        if fullname in sys.modules:
            patch_module(fullname)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.hooks:
            return None  # let python use another import hook to import this fullname

        # skip all finders before this one
        idx = sys.meta_path.index(self)
        for finder in sys.meta_path[idx + 1:]:
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                # we found a spec, change the loader

                def exec_module(module: ModuleType, exec_module=spec.loader.exec_module) -> None:
                    exec_module(module)
                    patch_module(module.__name__)

                spec.loader = SimpleNamespace(create_module=spec.loader.create_module, exec_module=exec_module)
                return spec
        raise ImportError(f"Could not load the module {fullname!r} to patch")


HOOK_IMPORT = PatchImportHook()
sys.meta_path.insert(0, HOOK_IMPORT)


def patch_init() -> None:
    os.environ['TZ'] = 'UTC'  # Set the timezone
    if hasattr(time, 'tzset'):
        time.tzset()

    for submodule in pkgutil.iter_modules(__path__):
        HOOK_IMPORT.add_hook(submodule.name)


def patch_module(name: str) -> None:
    module = importlib.import_module(f'.{name}', __name__)
    module.patch_module()
