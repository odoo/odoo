import os
import time
from pathlib import Path

from odoo.modules.migration import load_script
from . import evented  # noqa: F401

modules = {}


def set_timezone_utc():
    os.environ['TZ'] = 'UTC'
    if hasattr(time, 'tzset'):
        time.tzset()


def patch_all():
    set_timezone_utc()

    # Import all modules in this folder
    for path in __path__:
        for file in Path(path).glob('*.py'):
            module_name = file.stem
            fq_name = f"{__name__}.{module_name}"
            if fq_name not in os.sys.modules:
                patcher_module = load_script(path, fq_name)

                # Apply the patch on the original module
                patcher_module.patch()

            # Save some info on the patched module for runtime inspection
            if module := os.sys.modules.get(module_name):
                module._patched = patcher_module
                modules[module_name] = module
