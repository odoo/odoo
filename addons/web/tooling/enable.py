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

def get_addon_path(addons_path):
    for addon_path in addons_path:
        if not addon_path:
            continue
        addon_path_path = Path(addon_path).expanduser()
        if addon_path_path.is_absolute():
            modules_path = addon_path_path
        else:
            modules_path = ODOO_PATH.joinpath(addon_path)
        odoo_from_addon = os.path.relpath(ODOO_PATH, start=modules_path.resolve())
        addon_modules = get_odoo_modules(modules_path)
        js_paths = dict()
        for m in addon_modules:
            js_paths.update(get_module_paths_aliases("", m))
        if js_paths:
            yield {
                'path_odoo_to_addon': modules_path,
                "path_addon_to_odoo": odoo_from_addon,
                "js_paths": js_paths,
            }

def get_module_paths_aliases(path, module):
    path = str(path)
    path = path + "/" if path else ""
    if module.joinpath("static/src").is_dir():
        key_src = f"@{module.name}/*"
        src = f"{path}{module.name}/static/src/*"
        yield key_src, [src]
    if module.joinpath("static/tests").is_dir():
        key_test = f"@{module.name}/../tests/*"
        test = f"{path}{module.name}/static/tests/*"
        yield key_test, [test]

def path_relative_to_odoo(to_odoo, path):
    if path.startswith("addons/"):
        return to_odoo + "/" + path
    return path

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--addons-path", required=False, default="")
    arg_parser.add_argument("--update-odoo", required=False, action="store_true")
    args = arg_parser.parse_args()

    odoo_modules = get_odoo_modules(ODOO_PATH.joinpath("addons"))
    with open("./_jsconfig.json", "r") as f:
        jsconfig_file = f.read()

    odoo_paths = dict()
    for module in odoo_modules:
        odoo_paths.update(get_module_paths_aliases("addons", module))

    for data in get_addon_path((args.addons_path or "").split(",")):
        js_config = json.loads(jsconfig_file)
        odoo_paths_local = {}
        for module, paths in odoo_paths.items():
            odoo_paths_local[module] = [path_relative_to_odoo(str(data["path_addon_to_odoo"]), p) for p in paths]

        paths = js_config["compilerOptions"].get("paths", {})
        for js_paths in [odoo_paths_local, data["js_paths"]]:
            paths.update(js_paths)
        js_config["compilerOptions"]["paths"] = paths

        include = js_config.get("include", [])
        for i, path in enumerate(include):
             include[i] = path_relative_to_odoo(str(data["path_addon_to_odoo"]), path)
        include.extend(["**/*.js", "**/*.ts"])
        js_config["include"] = include

        exclude = js_config.get("exclude", [])
        for i, path in enumerate(exclude):
             exclude[i] = path_relative_to_odoo(str(data["path_addon_to_odoo"]), path)
        js_config["exclude"] = exclude

        with open(data["path_odoo_to_addon"].joinpath("jsconfig.json"), "w+") as f:
            f.write(json.dumps(js_config, indent=2))

    if args.update_odoo:
        js_config = json.loads(jsconfig_file)
        paths = js_config["compilerOptions"].get("paths", {})
        paths.update(odoo_paths)
        js_config["compilerOptions"]["paths"] = paths
        with open(ODOO_PATH.joinpath("jsconfig.json"), "w+") as f:
            f.write(json.dumps(js_config, indent=2))
