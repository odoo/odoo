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
        if not submodule.name.startswith('_'):
            HOOK_IMPORT.add_hook(submodule.name)

    patch_module('_cpython')

<<<<<<< 5d4238315bf8dd8fc5de645cf54527f395b81327

def patch_module(name: str) -> None:
    module = importlib.import_module(f'.{name}', __name__)
    module.patch_module()
||||||| 06fc4e71f1334a7fb876260792c5e47bdf37bf66
    from .codecs import patch_codecs
    patch_codecs()
    from .email import patch_email
    patch_email()
    from .mimetypes import patch_mimetypes
    patch_mimetypes()
    from .pytz import patch_pytz
    patch_pytz()
    from .literal_eval import patch_literal_eval
    patch_literal_eval()
    from .lxml import patch_lxml
    patch_lxml()
    from .num2words import patch_num2words
    patch_num2words()
    from .stdnum import patch_stdnum
    patch_stdnum()
    from .urllib3 import patch_urllib3
    patch_urllib3()
    from .werkzeug_urls import patch_werkzeug
    patch_werkzeug()
    from .zeep import patch_zeep
    patch_zeep()
    from .markupsafe import patch_markup
    patch_markup()
    from .requests import patch_requests
    patch_requests()
    from .pyopenssl import patch_pyopenssl
    patch_pyopenssl()
    from ._cpython import patch_cpython
    patch_cpython()
=======
    from .codecs import patch_codecs
    patch_codecs()
    from .email import patch_email
    patch_email()
    from .mimetypes import patch_mimetypes
    patch_mimetypes()
    from .pytz import patch_pytz
    patch_pytz()
    from .babel import patch_module as patch_babel
    patch_babel()
    from .literal_eval import patch_literal_eval
    patch_literal_eval()
    from .lxml import patch_lxml
    patch_lxml()
    from .num2words import patch_num2words
    patch_num2words()
    from .stdnum import patch_stdnum
    patch_stdnum()
    from .urllib3 import patch_urllib3
    patch_urllib3()
    from .werkzeug_urls import patch_werkzeug
    patch_werkzeug()
    from .zeep import patch_zeep
    patch_zeep()
    from .markupsafe import patch_markup
    patch_markup()
    from .requests import patch_requests
    patch_requests()
    from .pyopenssl import patch_pyopenssl
    patch_pyopenssl()
    from ._cpython import patch_cpython
    patch_cpython()
>>>>>>> 37b6f6f1bdbc6adf4454f2de50696d51140cd071
