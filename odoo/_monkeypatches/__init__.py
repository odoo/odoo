import os
import time
from pathlib import Path


class Monkeypatch():

    cwd = Path(__path__[0]).absolute()
    modules = {}

    @classmethod
    def patch_module(cls, module_name):
        fq_patcher = f"{__name__}.{module_name.replace('.', '_')}"
        if patcher_module := os.sys.modules.get(fq_patcher):
            return {}

        # Import the monkeypatcher module
        __import__(fq_patcher)

        # Patch the related module
        patcher_module = os.sys.modules.get(fq_patcher)
        if not (patched_modules := patcher_module.patch()):
            return {}

        cls.modules.update(patched_modules)

        # Save some info on the patched module for runtime inspection
        for patched_module in patched_modules.values():
            patched_module._patched = True

        return patched_modules

    @classmethod
    def patch_pre(cls):
        """ Import all modules in this folder but werkzeug_urls
            which has to be patched after odoo.tools are loaded
        """
        cls.patch_module('evented')

        os.environ['TZ'] = 'UTC'
        if hasattr(time, 'tzset'):
            time.tzset()

        excluded_names = ('__init__', 'evented', 'werkzeug_urls')
        excluded = {cls.cwd / f"{name}.py" for name in excluded_names}
        modules_paths = set(cls.cwd.glob('*.py')) - excluded
        for module_path in modules_paths:
            cls.patch_module(module_path.stem)
