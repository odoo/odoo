import argparse
import contextlib
import re
import logging
import sys
from inspect import cleandoc
from contextlib import closing, contextmanager
from pathlib import Path

import odoo.init  # import first for core setup
import odoo.cli
from odoo.modules import initialize_sys_path, load_script
from odoo.tools import config
from odoo.modules.registry import Registry


COMMAND_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$', re.I)
PROG_NAME = Path(sys.argv[0]).name
commands = {}


class CommandOpsMixin():
    allow_config_file = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.allow_config_file:
            self.parser.add_argument('-c', dest='config',
                help='Use a specific configuration file')

    def parse_args(self, cmdargs):
        try:
            parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        odoo.tools.config.parse_config(["-c", parsed_args.config] if self.allow_config_file else [])

        return parsed_args

    @contextmanager
    def build_env(
        self,
        db_name=None,
        update_module=False,
        install_modules=False,
        upgrade_modules=False,
        min_log_level=None
    ):
        if min_log_level:
            logging.disable(min_log_level)

        if not db_name:
            db_names = odoo.tools.config['db_name']
            if len(db_names) > 1:
                self.die("Please provide a single database in the config file.")
            db_name = db_names[0]

        registry = Registry.new(
            db_name,
            update_module=update_module,
            install_modules=install_modules or [],
            upgrade_modules=upgrade_modules or [],
        )
        with closing(registry.cursor()) as cr:
            yield odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        if min_log_level:
            logging.disable(logging.NOTSET)

    @staticmethod
    def die(message=None):
        if message:
            sys.exit(message)
        sys.exit(0)


class Command(CommandOpsMixin):
    name = None
    description = None
    epilog = None
    _parser = None
    subcommands = []

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        module = cls.__module__.rpartition('.')[2]
        if not cls.is_valid_name(cls.name):
            raise ValueError(
                f"Command name {cls.name!r} "
                f"must match {COMMAND_NAME_RE.pattern!r}")
        if cls.name != module:
            raise ValueError(
                f"Command name {cls.name!r} "
                f"must match Module name {module!r}")
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

    @classmethod
    def is_valid_name(cls, name):
        return re.match(COMMAND_NAME_RE, name)

    def run(self, cmdargs):
        """
            Executes the command.

            If this command has subcommands (like 'git remote add'), it finds and runs the
            specified subcommand. For example, if cmdargs is ['add', 'origin', 'url'],
            it will run the 'add' subcommand with ['origin', 'url'] as its arguments.

            If this command has no subcommands (like 'git status'), this method *must* be
            overridden by a subclass to provide the command's functionality.
        """
        if self.subcommands:
            self._config = odoo.tools.config.parse_config(None, setup_logging=True)
            self.subparsers = self.parser.add_subparsers(dest='subcommand', help='Subcommands help')
            assert(isinstance(self.subcommands, list | tuple))
            initialized_subcommands = {sc.name: sc for Cls in self.subcommands if (sc := Cls(self))}
            parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
            if subcommand := initialized_subcommands.get(parsed_args.subcommand):
                subcommand.run(cmdargs[1:])
            else:
                self.parser.print_help()
                Command.die()
        else:
            raise NotImplementedError()


class Subcommand(CommandOpsMixin):
    description = None

    @property
    def name(self):
        parent_name = self.parent_command.name
        classname = self.__class__.__name__
        return classname.lower().replace(parent_name.lower(), "")

    def __init__(self, parent_command, *args, **kwargs):
        if not getattr(self, 'description', None):
            logging.warning('No description found for class %s', self.__class__.__name__)
        self.parent_command = parent_command
        description = cleandoc(self.description or self.__doc__ or "")
        self.parser = self.parent_command.subparsers.add_parser(self.name, description=description)
        super().__init__(*args, **kwargs)


def load_internal_commands():
    """ Load ``commands`` from ``odoo.cli`` """
    for path in odoo.cli.__path__:
        for module in Path(path).iterdir():
            if module.suffix != '.py':
                continue
            __import__(f'odoo.cli.{module.stem}')


def load_addons_commands(command=None):
    """
    Search the addons path for modules with a ``cli/{command}.py`` file.
    In case no command is provided, discover and load all the commands.
    """
    if command is None:
        command = '*'
    elif not Command.is_valid_name(command):
        return

    mapping = {}
    initialize_sys_path()
    for path in odoo.addons.__path__:
        for fullpath in Path(path).glob(f'*/cli/{command}.py'):
            if (found_command := fullpath.stem) and Command.is_valid_name(found_command):
                # loading as odoo.cli and not odoo.addons.{module}.cli
                # so it doesn't load odoo.addons.{module}.__init__
                mapping[f'odoo.cli.{found_command}'] = fullpath 

    for fq_name, fullpath in mapping.items():
        with contextlib.suppress(ImportError):
            load_script(fullpath, fq_name)


def find_command(name: str) -> Command | None:
    """ Get command by name. """

    # built-in commands
    if command := commands.get(name):
        return command

    # import from odoo.cli
    with contextlib.suppress(ImportError):
        __import__(f'odoo.cli.{name}')
        return commands[name]

    # import from odoo.addons.*.cli
    load_addons_commands(command=name)
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
        command().run(args)
    else:
        message = (
            f"Unknown command {command_name!r}.\n"
            f"Use '{PROG_NAME} --help' to see the list of available commands."
        )
        Command.die(message)
