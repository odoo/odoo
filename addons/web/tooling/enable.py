#!/usr/bin/env python3
import argparse
import sys
import logging
from cli import commands, get_absolute_path, CONFIG

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("Web Tooling")


def process_addons_path(path_str):
    for path in path_str.split(","):
        if path:
            yield get_absolute_path(path)


def get_odoo_root_if_true(path):
    if path.joinpath("odoo-bin").exists():
        return path, path.joinpath("addons")
    if path.joinpath("web/__manifest__.py").exists():
        return path.joinpath(".."), path
    if path.joinpath("base/__manifest__.py").exists():
        return path.joinpath("../.."), path
    return None, None


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()

    available_commands = ["all"]
    for name, cls in commands.items():
        available_commands.append(name)
        if hasattr(cls, "configure"):
            cls.configure(arg_parser)
    arg_parser.add_argument(dest="command", choices=available_commands)
    arg_parser.add_argument(dest="operation", default="install", choices=["install", "remove"])
    arg_parser.add_argument("--addons-path", default="")

    args = arg_parser.parse_args()

    odoo = None
    addons_path = {}
    for path in process_addons_path(args.addons_path):
        odoo_path, real_addons_path = get_odoo_root_if_true(path)
        if odoo_path:
            path = real_addons_path
            if odoo is None:
                odoo = odoo_path
        addons_path[path] = {}

    if odoo is None:
        addons_path[CONFIG["odoo"].joinpath("addons")] = {}
    else:
        CONFIG["odoo"] = odoo

    logger.info("Launched on Odoo: %(odoo)s with addons paths: %(addonspath)s", dict(odoo=str(CONFIG["odoo"]), addonspath=", ".join(str(p) for p in addons_path)))

    command = args.command
    if command == "all":
        for cmd in commands.values():
            cmd().execute(addons_path, args.operation, args)
    else:
        cmd = commands[args.command]()
        cmd.execute(addons_path, args.operation, args)
