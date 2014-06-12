import logging
import sys
import os

import openerp
from openerp import tools
from openerp.modules import module

_logger = logging.getLogger(__name__)

commands = {}

class CommandType(type):
    def __init__(cls, name, bases, attrs):
        super(CommandType, cls).__init__(name, bases, attrs)
        name = getattr(cls, name, cls.__name__.lower())
        cls.name = name
        if name != 'command':
            commands[name] = cls

class Command(object):
    """Subclass this class to define new openerp subcommands """
    __metaclass__ = CommandType

    def run(self, args):
        pass

class Help(Command):
    """Display the list of available commands"""
    def run(self, args):
        print "Available commands:\n"
        padding = max([len(k) for k in commands.keys()]) + 2
        for k, v in commands.items():
            print "    %s%s" % (k.ljust(padding, ' '), v.__doc__ or '')
        print "\nUse '%s <command> --help' for individual command help." % sys.argv[0].split(os.path.sep)[-1]

import server
import deploy
import scaffold
import start

def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if len(args) > 1 and args[0].startswith('--addons-path=') and not args[1].startswith("-"):
        # parse only the addons-path, do not setup the logger...
        tools.config._parse_config([args[0]])
        args = args[1:]

    # Default legacy command
    command = "server"

    # Subcommand discovery
    if len(args) and not args[0].startswith("-"):
        logging.disable(logging.CRITICAL)
        for m in module.get_modules():
            m = 'openerp.addons.' + m
            __import__(m)
            #try:
            #except Exception, e:
            #    raise
            #    print e
        logging.disable(logging.NOTSET)
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        o.run(args)

# vim:et:ts=4:sw=4:
