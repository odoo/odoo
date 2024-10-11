#!/usr/bin/env python3

import os
from pathlib import Path
import argparse
import json

TOOLING_PATH = Path(os.path.abspath(__file__)).parent
ODOO_PATH = TOOLING_PATH.parent.parent.parent

def get_odoo_modules(path):
    for addon in path.iterdir():
        if not addon.is_dir():
            continue
        if addon.name.startswith("l10n_") or addon.name.startswith("test_"):
            continue
        yield addon

with open("./_jsconfig.json", "r") as f:
    jsconfig_file = f.read()

ODOO_MODULES = get_odoo_modules(ODOO_PATH.joinpath("addons"))

def make_js_config_module_paths(addons_path):
    for addon_path in addons_path:
        if not addon_path:
            continue
        addon_path_path = Path(addon_path)
        if addon_path_path.is_absolute():
            modules_path = addon_path_path
            odoo_from_addon = ODOO_PATH
        else:
            modules_path = ODOO_PATH.joinpath(addon_path)
            odoo_from_addon = os.path.relpath(ODOO_PATH, start=modules_path.resolve())
        addon_modules = get_odoo_modules(modules_path)
        js_paths = {}
        for path, modules in [(Path(odoo_from_addon).joinpath("addons"), ODOO_MODULES), ("", addon_modules)]:
            for m in modules:
                js_paths.update(get_module_paths_aliases(path, m))
        yield addon_path, addon_path_path, js_paths

def get_module_paths_aliases(path, module):
    path = str(path)
    path = path + "/" if path else ""
    result = {}
    key_src = f"@{module.name}/*"
    src = f"{path}{module.name}/static/src/*"
    result[key_src] = [src]

    key_test = f"@{module.name}/../tests/*"
    test = f"{path}{module.name}/static/tests/*"
    result[key_test] = [test]
    return result

print(__name__)
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--addons-path", required=False, default="../enterprise")
    args = arg_parser.parse_args()
    print(args)

    for t in make_js_config_module_paths((args.addons_path or "").split(",")):
        print(t)