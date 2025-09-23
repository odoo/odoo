# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
import sys
from pathlib import Path

import odoo
from odoo.modules import get_modules, get_module_path, initialize_sys_path

commands = {}
class Command:
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
        padding = max([len(cmd) for cmd in commands]) + 2
        command_list = "\n    ".join([
            "    {}{}".format(name.ljust(padding), (command.__doc__ or "").strip())
            for name, command in sorted(commands.items())
        ])
        print(ODOO_HELP.format(  # pylint: disable=bad-builtin
            odoo_bin=Path(sys.argv[0]).name,
            command_list=command_list
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
                __import__('odoo.addons.' + module)
        logging.disable(logging.NOTSET)
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        odoo.cli.COMMAND = command
        o.run(args)
    else:
        sys.exit('Unknown command %r' % (command,))
