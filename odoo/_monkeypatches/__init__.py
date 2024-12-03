import os
import time
from pathlib import Path

from . import evented  # noqa: F401

modules = {}


def set_timezone_utc():
    os.environ['TZ'] = 'UTC'
    if hasattr(time, 'tzset'):
        time.tzset()


def patch_all():
    set_timezone_utc()

    # Fetch all the modules in this folder
    mapping = [
        (module_name, fq_name)
        for path in __path__
        for x in Path(path).glob('*.py')
        if (module_name := x.stem)
        and not module_name.startswith("__")
        and (fq_name := f"{__name__}.{module_name}")
        and fq_name not in os.sys.modules
    ]

    for module_name, fq_name in mapping:
        # Import the monkeypatcher module
        __import__(fq_name)
        # Retrieve the loaded monkeypatcher module
        patcher_module = os.sys.modules[fq_name]
        # Patch the related module
        patched_modules = patcher_module.patch()
        # Save some info on the patched module for runtime inspection
        for fq_name, patched_module in patched_modules.items():
            patched_module._patched = True
            modules[fq_name] = patched_module
