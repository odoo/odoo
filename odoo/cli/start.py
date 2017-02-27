#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import glob
import itertools
import os
import sys

from . import Command
from .server import main
from odoo.modules.module import get_module_root, MANIFEST_NAMES
from odoo.service.db import _create_empty_database, DatabaseExists


class Start(Command):
    """Quick start the Odoo server for your project"""

    def get_module_list(self, path):
        mods = itertools.chain.from_iterable(
            glob.glob(os.path.join(path, '*/%s' % mname))
            for mname in MANIFEST_NAMES
        )
        return [mod.split(os.path.sep)[-2] for mod in mods]

    def run(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s start" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__
        )
        parser.add_argument('--path', default=".",
            help="Directory where your project's modules are stored (will autodetect from current dir)")
        parser.add_argument("-d", "--database", dest="db_name", default=None,
                         help="Specify the database name (default to project's directory name")


        args, unknown = parser.parse_known_args(args=cmdargs)

        project_path = os.path.abspath(os.path.expanduser(os.path.expandvars(args.path)))
        module_root = get_module_root(project_path)
        db_name = None
        if module_root:
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
        except DatabaseExists, e:
            pass
        except Exception, e:
            die("Could not create database `%s`. (%s)" % (args.db_name, e))

        if '--db-filter' not in cmdargs:
            cmdargs.append('--db-filter=^%s$' % args.db_name)

        # Remove --path /-p options from the command arguments
        def to_remove(i, l):
            return l[i] == '-p' or l[i].startswith('--path') or \
                (i > 0 and l[i-1] in ['-p', '--path'])
        cmdargs = [v for i, v in enumerate(cmdargs)
                   if not to_remove(i, cmdargs)]

        main(cmdargs)

def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)
