import logging
import sys

import openerp

_logger = logging.getLogger(__name__)

commands = {}

class CommandType(type):
    def __init__(cls, name, bases, attrs):
        super(CommandType, cls).__init__(name, bases, attrs)
        name = cls.__name__.lower()
        commands[name] = cls

class Command(object):
    __metaclass__ = CommandType

    def run():
        pass

import server

def main():
    args = sys.argv[1:]
    command = "server"
    if len(args) and not args[0].startswith("-"):
        command = args[0]
        args = args[1:]

    if command in commands:
        o = commands[command]()
        o.run(args)

# vim:et:ts=4:sw=4:
