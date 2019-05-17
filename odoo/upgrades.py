# -*- coding: utf-8 -*-
import importlib.util
import os
import sys

from odoo.tools import config
from odoo.modules.module import get_resource_path

for path in config.get("upgrades_paths", "").split(","):
    if os.path.exists(os.path.join(path, "__init__.py")):
        break
else:
    # failback to legacy "maintenance/migrations" package
    path = get_resource_path("base", "maintenance", "migrations")

if not path:
    raise ImportError("No package found in `upgrades_paths`")

spec = importlib.util.spec_from_file_location("odoo.upgrades", os.path.join(path, "__init__.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# shadow module and register under legacy name
sys.modules["odoo.upgrades"] = sys.modules["odoo.addons.base.maintenance.migrations"] = module
