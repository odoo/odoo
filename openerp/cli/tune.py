#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import argparse
import os
import re
import sys
import multiprocessing
import jinja2

from . import Command
from scaffold import snake, pascal, directory, template

import openerp
from openerp import tools

class Tune(Command):
    """ Generates an Odoo configuration skeleton. """

    def run(self, cmdargs):
        # TODO: bash completion file
        parser = argparse.ArgumentParser(
            prog="%s tune" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__,
        )
        parser.add_argument('hostname', help="Name of the web host")
        parser.add_argument('--rpcport', help="RPC port (default: %(default)s)", default="8069", nargs='?')
        parser.add_argument('--longpoll', help="Longpolling port (default: %(default)s)", default="8072", nargs='?')
        ssl_parser = parser.add_mutually_exclusive_group(required=False)
        ssl_parser.add_argument('--ssl', dest='ssl', action='store_true', help="Enable ssl support (default value)")
        ssl_parser.add_argument('--no-ssl', dest='ssl', action='store_false', help="Disable ssl support")
        parser.set_defaults(ssl=True)
        pos_parser = parser.add_mutually_exclusive_group(required=False)
        pos_parser.add_argument('--pos', dest='pos', action='store_true', help="Enable http for pos(default value)")
        pos_parser.add_argument('--no-pos', dest='pos', action='store_false', help="Disable http for pos")
        parser.set_defaults(pos=True)
        parser.add_argument(
            '--dest', default='.', nargs='?',
            help="Directory to create the configurations in (default: %(default)s)")

        if not cmdargs:
            sys.exit(parser.print_help())
            
        args = parser.parse_args(args=cmdargs)

        opts = {
            'hostname': args.hostname,
            'ssl': args.ssl,
            'pos': args.pos,
            'port': args.rpcport,
            'longpoll_port': args.longpoll,
            'workers': (max(multiprocessing.cpu_count(), 2) * 2) - 1,
        }
        
        tune_template('.').render_to(
            '.',
            directory(args.dest, create=True),
            opts)
            
        for thetool in ('nginx', 'logrotate', 'trululu'):
            try:
                tools.find_in_path(thetool)
            except IOError:
                logging.warning('Warning : Unable to find %r in path' % (thetool,))
            

builtins = lambda *args: os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'conf',
    *args)
    
env = jinja2.Environment()
env.filters['snake'] = snake
env.filters['pascal'] = pascal

class tune_template(template):
    def __init__(self, identifier):
        # TODO: archives (zipfile, tarfile)
        self.id = identifier
        # is identifier a builtin?
        self.path = builtins()
        if os.path.isdir(self.path):
            return
        # is identifier a directory?
        self.path = identifier
        if os.path.isdir(self.path):
            return
        die("{} is not a valid module template".format(identifier))
        
def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)

def warn(message):
    # ASK: shall we use logger ?
    print "WARNING: " + message
