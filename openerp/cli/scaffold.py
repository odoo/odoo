#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import functools
import keyword
import os
import re
import sys

import jinja2

from . import Command

class Scaffold(Command):
    "Generate an Odoo module skeleton."

    def __init__(self):
        super(Scaffold, self).__init__()
        env = jinja2.Environment(loader=jinja2.PackageLoader(
            'openerp.cli', 'scaffold'))
        env.filters['snake'] = snake
        self.env = env

    def scaffold(self, args):
        # TODO: make this function callable even if the module already
        #       exists. (update mode for scaffolding)
        from pudb import set_trace;set_trace() ############################## Breakpoint ##############################
        args.dependency = 'base'
        if args.web:
            args.dependency = 'web'
        elif args.theme:
            args.dependency = 'website'
        dest = os.path.abspath(os.path.expanduser(args.dest))

        module_name = snake(args.module)
        module = functools.partial(os.path.join, dest, module_name)

        if os.path.exists(module()):
            message = "The path `%s` already exists." % module()
            die(message)

        self.dump('__openerp__.jinja2', module('__openerp__.py'), config=args)
        self.dump('__init__.jinja2', module('__init__.py'), modules=[
            args.controller and 'controllers',
            args.model and 'models'
        ])
        self.dump('ir.model.access.jinja2', module('security', 'ir.model.access.csv'), config=args)


    def dump(self, template, dest, **kwargs):
        outdir = os.path.dirname(dest)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        self.env.get_template(template).stream(**kwargs).dump(dest)
        # add trailing newline which jinja removes
        with open(dest, 'a') as f:
            f.write('\n')

    def run(self, args):
        parser = argparse.ArgumentParser(
            prog="%s scaffold" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__
        )
        parser.add_argument('module', help="Name of the module to generate")
        parser.add_argument('dest', nargs='?', help='Directory where the module should be created (default to current directory)', default=".")


        if not args:
            sys.exit(parser.print_help())

        args = parser.parse_args(args=args)

        self.scaffold(args)

def snake(s):
    """ snake cases ``s``

    :param str s:
    :return: str
    """
    # insert a space before each uppercase character preceded by a
    # non-uppercase letter
    s = re.sub(r'(?<=[^A-Z])\B([A-Z])', r' \1', s)
    # lowercase everything, split on whitespace and join
    return '_'.join(s.lower().split())

def identifier(s):
    if keyword.iskeyword(s):
        die("%s is a Python keyword and can not be used as a name" % s)
    if not re.match('[A-Za-z_][A-Za-z0-9_]*', s):
        die("%s is not a valid Python identifier" % s)
    return s

def directory(p):
    expanded = os.path.abspath(
        os.path.expanduser(
            os.path.expandvars(p)))
    if not os.path.exists(expanded):
        os.makedirs(expanded)
    if not os.path.isdir(expanded):
        die("%s exists but is not a directory" % p)
    return expanded

def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)
