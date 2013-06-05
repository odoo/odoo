import logging
import sys

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
    def run(self, args):
        print "Available commands:\n"
        for k, v in commands.items():
            print "    %s" % k

import server

def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if len(args) > 1 and args[0].startswith('--addons-path=') and not args[1].startswith("-"):
        tools.config.parse_config([args[0]])
        args = args[1:]

    # Default legacy command
    command = "server"

    # Subcommand discovery
    if len(args) and not args[0].startswith("-"):
        for m in module.get_modules():
            m = 'openerp.addons.' + m
            __import__(m)
            #try:
            #except Exception, e:
            #    raise
            #    print e
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        o.run(args)

# vim:et:ts=4:sw=4:
