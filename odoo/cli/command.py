# ruff: noqa: PLC0415

import argparse
import contextlib
import logging
import os
import sys
import textwrap
from pathlib import Path

import odoo.cli
from odoo import api
from odoo.modules import get_module_path, get_modules, initialize_sys_path

commands = {}


class Command:
    name = None
    sys = sys
    os = os

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        commands[cls.name] = cls

    def __getattr__(self, name):
        delegated = {
            sys: ('argv', 'exit', 'stdin', 'stdout', 'stderr'),
        }
        for module, delegated_attrs in delegated.items():
            if name in delegated_attrs and hasattr(module, name):
                return getattr(module, name)

    @property
    def appname(self):
        return Path(self.argv[0]).name

    @property
    def title(self):
        return f'{self.appname} {self.name}'

    def documentation(self):
        raise NotImplementedError()

    def cleanup_string(self, s):
        return textwrap.dedent(s.lstrip("\n").rstrip())

    def new_parser(self, title=None, description=None):
        title = title or self.title
        description = description if description is not None else self.cleanup_string(self.documentation())
        return argparse.ArgumentParser(
            prog=title,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter)

    @classmethod
    def load_internal_commands(cls):
        """Load `commands` from `odoo.cli`"""
        for path in odoo.cli.__path__:
            for module in Path(path).iterdir():
                if module.suffix != '.py' or module.name.startswith("_"):
                    continue
                __import__(f'odoo.cli.{module.stem}')

    @classmethod
    def load_addons_commands(cls):
        """Load `commands` from `odoo.addons.*.cli`"""
        logging.disable(logging.CRITICAL)
        initialize_sys_path()
        for module in get_modules():
            if (Path(get_module_path(module)) / 'cli').is_dir():
                with contextlib.suppress(ImportError):
                    __import__(f'odoo.addons.{module}')
        logging.disable(logging.NOTSET)
        return list(commands)

    @classmethod
    def find_command(cls, name: str) -> api.Self | None:
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
        cls.load_addons_commands()
        return commands.get(name)
