# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import re
import sys
from pathlib import Path

import odoo.cli
from odoo.modules import initialize_sys_path, load_script


COMMAND_NAME_RE = re.compile(r"^[a-zA-Z0-9\-_]+$")

commands = {}
"""All loaded commands"""


class Command:
    name = None
    prog_name = Path(sys.argv[0]).name

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        if not COMMAND_NAME_RE.match(cls.name):
            raise ValueError(
                f"command name must match {COMMAND_NAME_RE.pattern}: "
                f"{cls.name!r}")
        if (modname := cls.__module__.rpartition('.')[2]) != cls.name:
            raise ValueError(
                f"command must be defined in a module of the same name: "
                f"{cls.name!r} vs {modname!r} ({cls.__module__})")
        commands[cls.name] = cls


def load_internal_commands():
    """Load `commands` from `odoo.cli`"""
    for path in odoo.cli.__path__:
        for module in Path(path).iterdir():
            if module.suffix != '.py':
                continue
            __import__(f'odoo.cli.{module.stem}')


def load_addons_commands():
    """Load `commands` from `odoo.addons.*.cli`"""
    initialize_sys_path()
    for addon_path in odoo.addons.__path__:
        for cli_path in Path(addon_path).glob('*/cli/*.py'):
            if cli_path.name == '__init__.py':
                continue
            app = cli_path.parents[1].name
            load_script(
                path=str(cli_path),
                module_name=f'odoo.addons.{app}.cli.{cli_path.stem}'
            )
    return list(commands)


def find_command(name: str) -> Command | None:
    """ Get command by name. """
    if not COMMAND_NAME_RE.match(name):
        e = f"invalid command name {name!r}"
        raise ValueError(e)
    # check in the loaded commands
    if command := commands.get(name):
        return command
    # import from odoo.cli
    with contextlib.suppress(ImportError):
        __import__(f'odoo.cli.{name}')
        return commands[name]
    # last try, find a odoo.addons.<module>.cli.<name>
    initialize_sys_path()
    for addon_path in odoo.addons.__path__:
        for cli_path in Path(addon_path).glob(f'*/cli/{name}.py'):
            app = cli_path.parents[1].name
            load_script(
                path=str(cli_path),
                module_name=f'odoo.addons.{app}.cli.{cli_path.stem}'
            )
    return commands.get(name)


def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if len(args) > 1 and args[0].startswith('--addons-path=') and not args[1].startswith('-'):
        # parse only the addons-path, do not setup the logger...
        odoo.tools.config._parse_config([args[0]])
        args = args[1:]

    if len(args) and not args[0].startswith('-'):
        # Command specified, search for it
        command_name = args[0]
        args = args[1:]
        if not COMMAND_NAME_RE.match(command_name):
            sys.exit(f"Invalid command: {command_name}")
    elif '-h' in args or '--help' in args:
        # No command specified, but help is requested
        command_name = 'help'
        args = [x for x in args if x not in ('-h', '--help')]
    else:
        # No command specified, default command used
        command_name = 'server'

    if command := find_command(command_name):
        o = command()
        o.run(args)
    else:
        sys.exit(f'Unknown command: {command_name}')
