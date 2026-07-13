# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import sys
import traceback
from pathlib import Path

import odoo
from odoo.modules import get_module_path, get_modules, initialize_sys_path

commands = {}
class Command:  # noqa: E302
    name = None

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        commands[cls.name] = cls


ODOO_HELP = """\
Odoo CLI, use '{odoo_bin} --help' for regular server options.

Available commands:
    {command_list}

Use '{odoo_bin} <command> --help' for individual command help."""


class Help(Command):
    """ Display the list of available commands """
    def run(self, args):
        padding = max(len(cmd) for cmd in commands) + 2
        command_list = "\n    ".join([
            "    {}{}".format(name.ljust(padding), (command.__doc__ or "").strip())
            for name, command in sorted(commands.items())
        ])
        print(ODOO_HELP.format(  # noqa: T201
            odoo_bin=Path(sys.argv[0]).name,
            command_list=command_list,
        ))


def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if len(args) > 1 and args[0].startswith('--addons-path=') and not args[1].startswith("-"):
        # parse only the addons-path, do not setup the logger...
        odoo.tools.config._parse_config([args[0]])
        args = args[1:]

    # Default legacy command
    command = "server"

    # TODO: find a way to properly discover addons subcommands without importing the world
    # Subcommand discovery
    if len(args) and not args[0].startswith("-"):
        logging.disable(logging.CRITICAL)
        initialize_sys_path()
        for module in get_modules():
            if (Path(get_module_path(module)) / 'cli').is_dir():
                try:
                    __import__('odoo.addons.' + module)
                except Exception:  # noqa: BLE001
                    print("Failed to scan module", module, file=sys.stderr)  # noqa: T201
                    if module == 'hw_drivers':
                        print("maybe a git clean -df addons/ can fix the problem", file=sys.stderr)  # noqa: T201
                    traceback.print_exc()
        logging.disable(logging.NOTSET)
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        odoo.cli.COMMAND = command
        o.run(args)
    else:
        sys.exit('Unknown command %r' % (command,))
