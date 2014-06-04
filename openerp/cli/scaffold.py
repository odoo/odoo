#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import ast
import functools
import keyword
import logging
import os
import re
import simplejson
import sys

import jinja2

from . import Command

from openerp.modules.module import (get_module_root, MANIFEST, load_information_from_description_file as load_manifest)


class Scaffold(Command):
    "Generate an Odoo module skeleton."

    def run(self, cmdargs):
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

        if not cmdargs:
            sys.exit(parser.print_help())
        args = parser.parse_args(args=cmdargs)

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

        logging.disable(logging.CRITICAL)
        scaffold = ScaffoldModule(dest)
        if args.model:
            scaffold.add_model(snake(args.model))
        if args.controller:
            scaffold.add_controller(args.controller)
        if args.web:
            scaffold.add_webclient_structure()
        if args.theme:
            scaffold.add_theme_structure()

class ScaffoldModule(object):
    """
    Object for scaffolding existing or new Odoo modules

    @param path: Path of an existing module or path of module to create
    """
    def __init__(self, path):
        env = jinja2.Environment(loader=jinja2.PackageLoader(
            'openerp.cli', 'scaffold'), keep_trailing_newline=True)
        env.filters['snake'] = snake
        self.env = env
        self.path = functools.partial(os.path.join, directory(path))
        self.created = not os.path.exists(self.path())
        directory(path, create=True)
        self.module = self.path().split(os.path.sep)[-1]
        if self.created:
            manifest_base = os.path.splitext(MANIFEST)[0]
            self.render_file('%s.jinja2' % manifest_base, self.path('%s.py' % manifest_base))
            # Create an empty __init__.py so the module can be imported
            open(self.path('__init__.py'), 'a').close()

    def add_model(self, model):
        model_module = snake(model)
        model_file = self.path('models', '%s.py' % model_module)
        if os.path.exists(model_file):
            die("Model `%s` already exists !" % model_file)
        self.add_init_import(self.path('__init__.py'), 'models')
        self.add_init_import(self.path('models', '__init__.py'), model_module)

        self.render_file('models.jinja2', model_file, model=model)
        self.render_file('ir.model.access.jinja2', self.path('security', 'ir.model.access.csv'),
                         if_exists='append', model=model)
        self.append_manifest_list('data', 'security/ir.model.access.csv')

        demo_file = 'data/%s_demo.xml' % self.module
        self.append_xml_data('record.jinja2', self.path(demo_file),
                             model=model)
        self.append_manifest_list('demo', demo_file)

    def add_controller(self, controller):
        controller_module = snake(controller)
        controller_file = self.path('controllers', '%s.py' % controller_module)
        if os.path.exists(controller_file):
            die("Controller `%s` already exists !" % controller_file)
        self.add_init_import(self.path('__init__.py'), 'controllers')
        # Check if the controller name correspond to a model and expose result to templates
        has_model = self.has_import(self.path('models', '__init__.py'), controller_module)
        self.add_init_import(self.path('controllers', '__init__.py'), controller_module)
        self.render_file('controllers.jinja2', controller_file, controller=controller,
                         has_model=has_model)

    def add_webclient_structure(self):
        self.append_manifest_list('depends', 'web')
        prefix = '%s.%%s' % self.module
        for ext in ('js', 'css', 'xml'):
            self.render_file('webclient_%s.jinja2' % ext,
                             self.path('static', 'src', ext, prefix % ext))

    def add_theme_structure(self):
        self.append_manifest_list('depends', 'website')
        css_file = '%s_theme.css' % self.module
        self.render_file('theme_css.jinja2', self.path('static', 'src', 'css', css_file))
        self.append_xml_data('theme_xml.jinja2', self.path('views', 'templates.xml'), skip_if_exist=True)
        self.append_manifest_list('data', 'views/templates.xml')

    def has_import(self, initfile, module):
        if not os.path.isfile(initfile):
            return False
        with open(initfile, 'r') as f:
            for imp in ast.parse(f.read()).body:
                if isinstance(imp, ast.Import):
                    if module in [mod.name for mod in imp.names]:
                        return True
        return False

    def get_manifest(self, key=None, default=None):
        manifest = load_manifest(self.module, self.path())
        if key:
            return manifest.get(key, default)
        else:
            return manifest

    def append_manifest_list(self, key, value, unique=True):
        # TODO: append value without altering serialized formatting
        vals = self.get_manifest(key, [])
        if unique and value in vals:
            return
        vals.append(value)
        self.change_manifest_key(key, vals)

    def change_manifest_key(self, key, value):
        value = simplejson.dumps(value)
        with open(self.path(MANIFEST), 'r') as f:
            data = f.read()
        sdata = re.split('["\']%s["\']\s?:\s?\[[^\]]*\]' % key, data)
        add = "'%s': %s" % (key, value)
        if len(sdata) != 2:
            warn("Could not update `%s` key in manifest. You should add this by yourself:"
                 "\n\n%s\n" % (key, add))
        else:
            with open(self.path(MANIFEST), 'w') as f:
                f.write(add.join(sdata))

    def add_init_import(self, initfile, module):
        if not(os.path.exists(initfile) and self.has_import(initfile, module)):
            self.render_file('__init__.jinja2', initfile, if_exists='append', modules=[module])

    def render_file(self, template, dest, if_exists='skip', **kwargs):
        mode = 'a'
        if os.path.exists(dest):
            if if_exists == 'replace':
                mode = 'w'
            elif if_exists != 'append':
                warn("File `%s` already exists. Skipping it..." % dest)
                return
        else:
            kwargs['file_created'] = True
        outdir = os.path.dirname(dest)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        content = self.env.get_template(template).render(module=self.module, **kwargs)
        with open(dest, mode) as f:
            f.write(content)

    def append_xml_data(self, template, dest, skip_if_exist=False, **kwargs):
        if not os.path.exists(dest):
            self.render_file('xmldata.jinja2', dest, **kwargs)
        elif skip_if_exist:
            warn("File `%s` already exists. Skipping it..." % dest)
        with open(dest, 'r') as f:
            data = f.read()
        m = re.search('(^\s*)?</data>', data, re.MULTILINE)
        content = self.env.get_template(template).render(module=self.module, **kwargs)
        if not m:
            warn("Could not add data in `%s`. You should add this by yourself:"
                 "\n\n%s\n" % (dest, content))
        else:
            data = data[:m.start()] + content + m.group() + data[m.end():]
            with open(self.path(dest), 'w') as f:
                f.write(data)

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

def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)

def warn(message):
    # ASK: shall we use logger ?
    print "WARNING: " + message

