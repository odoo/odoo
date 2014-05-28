#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import ast
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
        self.manifest = '__openerp__'

    def scaffold(self, args):
        args.dependency = 'base'
        # TODO: update dependencies according to --web and --theme
        # if args.web:
        #     args.dependency = 'web'
        # elif args.theme:
        #     args.dependency = 'website'

        dest = directory(args.dest)
        if args.init:
            module_name = snake(args.init)
            module = functools.partial(os.path.join, dest, module_name)
            if os.path.exists(module()):
                die("Can't initialize module in `%s`: Directory already exists." % module())
        else:
            module_name = dest.split(os.path.sep)[-1]
            # find the module's root directory
            while not os.path.exists(os.path.join(dest, '%s.py' % self.manifest)):
                new_dest = os.path.abspath(os.path.join(dest, os.pardir))
                if dest == new_dest:
                    die("Can't find module directory. Please `cd` to it's path or use --dest")
                module_name = dest.split(os.path.sep)[-1]
                dest = new_dest
            module = functools.partial(os.path.join, dest)
        args.module = module_name

        if args.init:
            self.dump('%s.jinja2' % self.manifest, module('%s.py' % self.manifest), config=args)

        if args.model:
            model_module = snake(args.model)
            model_file = module('models', '%s.py' % model_module)
            if os.path.exists(model_file):
                die("Model `%s` already exists !" % model_file)
            self.add_init_import(module('__init__.py'), 'models')
            self.add_init_import(module('models', '__init__.py'), model_module)
            self.dump('models.jinja2', model_file, config=args)
            self.dump('ir.model.access.jinja2', module('security', 'ir.model.access.csv'), config=args)

        if args.controller:
            controller_module = snake(args.controller)
            controller_file = module('controllers', '%s.py' % controller_module)
            if os.path.exists(controller_file):
                die("Controller `%s` already exists !" % controller_file)
            self.add_init_import(module('__init__.py'), 'controllers')
            # Check if the controller name correspond to a model and expose result to templates
            args.has_model = self.has_import(module('models', '__init__.py'), controller_module)
            self.add_init_import(module('controllers', '__init__.py'), controller_module)
            self.dump('controllers.jinja2', module('controllers', controller_file), config=args)

    def has_import(self, initfile, module):
        with open(initfile, 'r') as f:
            for imp in ast.parse(f.read()).body:
                if isinstance(imp, ast.Import):
                    if module in [mod.name for mod in imp.names]:
                        return True
        return False

    def add_init_import(self, initfile, module):
        if not(os.path.exists(initfile) and self.has_import(initfile, module)):
            self.dump('__init__.jinja2', initfile, modules=[module])

    def dump(self, template, dest, **kwargs):
        outdir = os.path.dirname(dest)
        kwargs['create'] = not os.path.exists(dest)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        content = self.env.get_template(template).render(**kwargs)
        with open(dest, 'a') as f:
            f.write(content)

    def run(self, args):
        # TODO: bash completion file
        parser = argparse.ArgumentParser(
            prog="%s scaffold" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__
        )
        parser.add_argument('--init', type=identifier, help='Initialize a new Odoo module')

        parser.add_argument('--dest', default=".",
            help='Directory where the module should be created/updated (default to current directory)')

        parser.add_argument('--model', type=identifier, help="Name of the model to add")

        parser.add_argument('--controller', type=identifier, help="Name of the controller to add")

        parser.add_argument('--web', action='store_true', default=False,
                         help="Generate structure for a webclient module")

        parser.add_argument('--theme', action='store_true', default=False,
                         help="Generate structure for a Website theme")

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
