import glob
import itertools
import os
import sys

from . import Command
from .server import main
from odoo.modules.module import Manifest, MANIFEST_NAMES
from odoo.service.db import _create_empty_database, DatabaseExists
from odoo.tools import config


class Start(Command):
    """ Quickly start the odoo server with default options """

    def get_module_list(self, path):
        mods = itertools.chain.from_iterable(
            glob.glob(os.path.join(path, '*/%s' % mname))
            for mname in MANIFEST_NAMES
        )
        return [mod.split(os.path.sep)[-2] for mod in mods]

    def run(self, cmdargs):
        config.parser.prog = self.prog
        self.parser.add_argument('--path', default=".",
            help="Directory where your project's modules are stored (will autodetect from current dir)")
        self.parser.add_argument("-d", "--database", dest="db_name", default=None,
            help="Specify the database name (default to project's directory name")

        args, _unknown = self.parser.parse_known_args(args=cmdargs)

        # When in a virtualenv, by default use it's path rather than the cwd
        if args.path == '.' and os.environ.get('VIRTUAL_ENV'):
            args.path = os.environ.get('VIRTUAL_ENV')
        project_path = os.path.abspath(os.path.expanduser(os.path.expandvars(args.path)))
        db_name = None
        if is_path_in_module(project_path):
            # started in a module so we choose this module name for database
            db_name = project_path.split(os.path.sep)[-1]
            # go to the parent's directory of the module root
            project_path = os.path.abspath(os.path.join(project_path, os.pardir))

        # check if one of the subfolders has at least one module
        mods = self.get_module_list(project_path)
        if mods and '--addons-path' not in cmdargs:
            cmdargs.append('--addons-path=%s' % project_path)

        if not args.db_name:
            args.db_name = db_name or project_path.split(os.path.sep)[-1]
            cmdargs.extend(('-d', args.db_name))

        # TODO: forbid some database names ? eg template1, ...
        try:
            _create_empty_database(args.db_name)
            config['init']['base'] = True
        except DatabaseExists as e:
            pass
        except Exception as e:
            sys.exit("Could not create database `%s`. (%s)" % (args.db_name, e))

        if '--db-filter' not in cmdargs:
            cmdargs.append('--db-filter=^%s$' % args.db_name)

        # Remove --path /-p options from the command arguments
        def to_remove(i, l):
            return l[i] == '-p' or l[i].startswith('--path') or \
                (i > 0 and l[i-1] in ['-p', '--path'])
        cmdargs = [v for i, v in enumerate(cmdargs)
                   if not to_remove(i, cmdargs)]

        main(cmdargs)


def is_path_in_module(path):
    old_path = None
    while path != old_path:
        if Manifest._from_path(path):
            return True
        old_path = path
        path, _ = os.path.split(path)
    return False
