import argparse
import logging
import sys
import traceback
from inspect import cleandoc
from pathlib import Path

import odoo.init  # import first for core setup  # noqa: F401
import odoo.cli
from odoo.modules import get_module_path, get_modules, initialize_sys_path
from odoo.tools import config

commands = {}
"""All loaded commands"""

PROG_NAME = Path(sys.argv[0]).name


class Command:
    name = None
    description = None
    epilog = None
    _parser = None

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        commands[cls.name] = cls

    @property
    def prog(self):
        return f"{PROG_NAME} [--addons-path=PATH,...] {self.name}"

    @property
    def parser(self):
        if not self._parser:
            self._parser = argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,
                prog=self.prog,
                description=cleandoc(self.description or self.__doc__ or ""),
                epilog=cleandoc(self.epilog or ""),
            )
        return self._parser


def load_internal_commands():
    """Load `commands` from `odoo.cli`"""
    for path in odoo.cli.__path__:
        for module in Path(path).iterdir():
            if module.suffix != '.py':
                continue
            __import__(f'odoo.cli.{module.stem}')


def load_addons_commands():
    """Load `commands` from `odoo.addons.*.cli`"""
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
    return list(commands)


def find_command(name: str) -> Command | None:
    """ Get command by name. """
    # check in the loaded commands
    if command := commands.get(name):
        return command
    # import from odoo.cli
    try:
        __import__(f'odoo.cli.{name}')
    except ImportError:
        pass
    else:
        if command := commands.get(name):
            return command
    # last try, import from odoo.addons.*.cli
    load_addons_commands()
    return commands.get(name)


def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if len(args) > 1 and args[0].startswith('--addons-path=') and not args[1].startswith('-'):
        # parse only the addons-path, do not setup the logger...
        config._parse_config([args[0]])
        args = args[1:]

    if len(args) and not args[0].startswith('-'):
        # Command specified, search for it
        command_name = args[0]
        args = args[1:]
    elif '-h' in args or '--help' in args:
        # No command specified, but help is requested
        command_name = 'help'
        args = [x for x in args if x not in ('-h', '--help')]
    else:
        # No command specified, default command used
        command_name = 'server'

    if command := find_command(command_name):
        odoo.cli.COMMAND = command_name
        o = command()
        o.run(args)
    else:
        sys.exit(f"Unknown command {command_name!r}")
