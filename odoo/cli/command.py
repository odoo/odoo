from __future__ import print_function
import logging
import sys
import os
from os.path import join as joinpath, isdir

import odoo
from odoo.modules import get_modules, get_module_path

commands = {}

class CommandType(type):
    def __init__(cls, name, bases, attrs):
        super(CommandType, cls).__init__(name, bases, attrs)
        name = getattr(cls, name, cls.__name__.lower())
        cls.name = name
        if name != 'command':
            commands[name] = cls

class Command(object):
    """Subclass this class to define new odoo subcommands """
    __metaclass__ = CommandType

    def run(self, args):
        pass

class Help(Command):
    """Display the list of available commands"""
    def run(self, args):
        print("Available commands:\n")
        names = commands.keys()
        padding = max([len(k) for k in names]) + 2
        for k in sorted(names):
            name = k.ljust(padding, ' ')
            doc = (commands[k].__doc__ or '').strip()
            print("    %s%s" % (name, doc))
        print("\nUse '%s <command> --help' for individual command help." % sys.argv[0].split(os.path.sep)[-1])

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
        for module in get_modules():
            if isdir(joinpath(get_module_path(module), 'cli')):
                __import__('odoo.addons.' + module)
        logging.disable(logging.NOTSET)
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        o.run(args)
    else:
        sys.exit('Unknow command %r' % (command,))
