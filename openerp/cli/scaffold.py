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

MANIFEST = '__openerp__'

class Scaffold(Command):
    "Generate an Odoo module skeleton."

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

        dest = directory(args.dest)
        if args.init:
            dest = os.path.join(dest, args.init)
            if os.path.exists(dest):
                die("Can't initialize module in `%s`: Directory already exists." % dest)
            if get_module_root(dest):
                die("Can't init a new module in another Odoo module, you probably want to run this "
                    "command from your project's root")
        else:
             mroot = get_module_root(dest)
             if not mroot:
                 die("The path `%s` provided does not point to an existing Odoo module. "
                     "Forgot to `--init` ?" % dest)
             dest = mroot

        scaffold = ScaffoldModule(dest)
        if args.model:
            scaffold.add_model(args.model)
        if args.controller:
            scaffold.add_controller(args.controller)

class ScaffoldModule(object):
    """
    Object for scaffolding existing or new Odoo modules

    @param path: Path of an existing module or path of module to create
    """
    def __init__(self, path):
        env = jinja2.Environment(loader=jinja2.PackageLoader(
            'openerp.cli', 'scaffold'))
        env.filters['snake'] = snake
        self.env = env
        self.path = functools.partial(os.path.join, directory(path))
        self.created = not os.path.exists(self.path())
        directory(path, create=True)
        if self.created:
            self.module_name = self.path().split(os.path.sep)[-1]
            self.dump('%s.jinja2' % MANIFEST, self.path('%s.py' % MANIFEST))
        else:
            # TODO: get this information from manifest
            self.module_name = self.path().split(os.path.sep)[-1]

    def add_model(self, model):
        model_module = snake(model)
        model_file = self.path('models', '%s.py' % model_module)
        if os.path.exists(model_file):
            die("Model `%s` already exists !" % model_file)
        self.add_init_import(self.path('__init__.py'), 'models')
        self.add_init_import(self.path('models', '__init__.py'), model_module)
        self.dump('models.jinja2', model_file, model=model)
        self.dump('ir.model.access.jinja2', self.path('security', 'ir.model.access.csv'), model=model)

    def add_controller(self, controller):
        controller_module = snake(controller)
        controller_file = self.path('controllers', '%s.py' % controller_module)
        if os.path.exists(controller_file):
            die("Controller `%s` already exists !" % controller_file)
        self.add_init_import(self.path('__init__.py'), 'controllers')
        # Check if the controller name correspond to a model and expose result to templates
        has_model = self.has_import(self.path('models', '__init__.py'), controller_module)
        self.add_init_import(self.path('controllers', '__init__.py'), controller_module)
        self.dump('controllers.jinja2', self.path('controllers', controller_file),
                  controller=controller, has_model=has_model)

    def has_import(self, initfile, module):
        with open(initfile, 'r') as f:
            for imp in ast.parse(f.read()).body:
                if isinstance(imp, ast.Import):
                    if module in [mod.name for mod in imp.names]:
                        return True
        return False

    def ensure_dependency_to(self, module):
        # TODO: update dependencies according to --web and --theme
        # if args.web:
        #     args.dependency = 'web'
        # elif args.theme:
        #     args.dependency = 'website'
        pass

    def add_init_import(self, initfile, module):
        if not(os.path.exists(initfile) and self.has_import(initfile, module)):
            self.dump('__init__.jinja2', initfile, modules=[module])

    def dump(self, template, dest, **kwargs):
        outdir = os.path.dirname(dest)
        kwargs['file_created'] = not os.path.exists(dest)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        content = self.env.get_template(template).render(module_name=self.module_name, **kwargs)
        with open(dest, 'a') as f:
            f.write(content)

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

def directory(p, create=False):
    expanded = os.path.abspath(
        os.path.expanduser(
            os.path.expandvars(p)))
    if create and not os.path.exists(expanded):
        os.makedirs(expanded)
    if create and not os.path.isdir(expanded):
        die("%s exists but is not a directory" % p)
    return expanded

def get_module_root(path):
    """
    Get closest module's root begining from path

    @param path: Path from which the lookup should start

    @return:  Module root path
    """
    # find the module's root directory
    while not os.path.exists(os.path.join(path, '%s.py' % MANIFEST)):
        new_path = os.path.abspath(os.path.join(path, os.pardir))
        if path == new_path:
            return None
        path = new_path
    return path


def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)
