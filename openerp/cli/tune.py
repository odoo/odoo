#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
import re
import sys
import multiprocessing
import jinja2

from . import Command
from scaffold import snake, pascal, directory

from openerp.modules.module import (get_module_root, MANIFEST, load_information_from_description_file as load_manifest)


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
        
        template('nginx.conf.template').render_to(
            directory(args.dest, create=True),
            opts)
        template('odoo.conf.template').render_to(
            directory(args.dest, create=True),
            opts)

builtins = lambda *args: os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'conf',
    *args)
    
env = jinja2.Environment()
env.filters['snake'] = snake
env.filters['pascal'] = pascal
class template(object):
    def __init__(self, identifier):
        self.id = identifier
        self.path = builtins(identifier)
        if os.path.isfile(self.path):
            return
        die("{} is not a valid template".format(identifier))

    def __str__(self):
        return self.id

    def render_to(self, directory, params=None):
        """ Render this template to ``dest`` with the provided
         rendering parameters
        """
        with open(self.path, 'rb') as content:
            local = self.id
            # strip .template extension
            root, ext = os.path.splitext(local)
            if ext == '.template':
                local = root
            dest = os.path.join(directory, local)
            destdir = os.path.dirname(dest)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            with open(dest, 'wb') as f:
                env.from_string(content.read().decode('utf-8'))\
                    .stream(params or {})\
                    .dump(f, encoding='utf-8')

def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)

def warn(message):
    # ASK: shall we use logger ?
    print "WARNING: " + message
