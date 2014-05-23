"""
Generate an OpenERP module skeleton.
"""

import functools
import keyword
import os
import re
import sys

import jinja2

# FIXME: add logging
def run(args):
    env = jinja2.Environment(loader=jinja2.PackageLoader(
        'openerpcommand', 'templates'))
    env.filters['snake'] = snake
    args.dependency = 'web' if args.controller else 'base'

    module_name = snake(args.module)
    module = functools.partial(
        os.path.join, args.modules_dir, module_name)

    if args.controller is True:
        args.controller = module_name

    if args.model is True:
        args.model = module_name

    if os.path.exists(module()):
        message = "The path `%s` already exists." % module()
        die(message)

    dump(env, '__openerp__.jinja2', module('__openerp__.py'), config=args)
    dump(env, '__init__.jinja2', module('__init__.py'), modules=[
        args.controller and 'controllers',
        args.model and 'models'
    ])
    dump(env, 'ir.model.access.jinja2', module('security', 'ir.model.access.csv'), config=args)

    if args.controller:
        controller_module = snake(args.controller)
        dump(env, '__init__.jinja2', module('controllers', '__init__.py'), modules=[controller_module])
        dump(env, 'controllers.jinja2',
             module('controllers', '%s.py' % controller_module),
             config=args)

    if args.model:
        model_module = snake(args.model)
        dump(env, '__init__.jinja2', module('models', '__init__.py'), modules=[model_module])
        dump(env, 'models.jinja2', module('models', '%s.py' % model_module), config=args)

def add_parser(subparsers):
    parser = subparsers.add_parser('scaffold',
        description='Generate an OpenERP module skeleton.')
    parser.add_argument('module', metavar='MODULE',
        help='the name of the generated module')
    parser.add_argument('modules_dir', metavar='DIRECTORY', type=directory,
        help="Modules directory in which the new module should be generated")

    controller = parser.add_mutually_exclusive_group()
    controller.add_argument('--controller', type=identifier,
        help="The name of the controller to generate")
    controller.add_argument('--no-controller', dest='controller',
        action='store_const', const=None, help="Do not generate a controller")

    model = parser.add_mutually_exclusive_group()
    model.add_argument('--model', type=identifier,
       help="The name of the model to generate")
    model.add_argument('--no-model', dest='model',
       action='store_const', const=None, help="Do not generate a model")

    mod = parser.add_argument_group("Module information",
        "these are added to the module metadata and displayed on e.g. "
        "apps.openerp.com. For company-backed modules, the company "
        "information should be used")
    mod.add_argument('--name', dest='author_name', default="",
                     help="Name of the module author")
    mod.add_argument('--website', dest='author_website', default="",
                     help="Website of the module author")
    mod.add_argument('--category', default="Uncategorized",
        help="Broad categories to which the module belongs, used for "
             "filtering within OpenERP and on apps.openerp.com."
             "Defaults to %(default)s")
    mod.add_argument('--summary', default="",
        help="Short (1 phrase/line) summary of the module's purpose, used as "
             "subtitle on modules listing or apps.openerp.com")

    parser.set_defaults(run=run, controller=True, model=True)

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

def dump(env, template, dest, **kwargs):
    outdir = os.path.dirname(dest)
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    env.get_template(template).stream(**kwargs).dump(dest)
    # add trailing newline which jinja removes
    with open(dest, 'a') as f:
        f.write('\n')

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
