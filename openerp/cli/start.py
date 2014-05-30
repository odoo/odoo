#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import glob
import os
import sys

from . import Command
from .server import main
from openerp.modules.module import get_module_root, MANIFEST
from openerp.service.db import _create_empty_database, DatabaseExists


class Start(Command):
    """Quick start the Odoo server for your project"""

    def get_module_list(self, path):
        mods = glob.glob(os.path.join(path, '*/%s' % MANIFEST))
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


        #openerp.tools.config.parse_config(args)
        args, unknown = parser.parse_known_args(args=cmdargs)

        project_path = os.path.abspath(os.path.expanduser(os.path.expandvars(args.path)))
        module_root = get_module_root(project_path)
        if module_root:
            # go to the parent's directory of the module root if any
            project_path = os.path.abspath(os.path.join(project_path, os.pardir))

        # check if one of the subfolders has at least one module
        mods = self.get_module_list(project_path)
        if not mods:
            die("Directory `%s` does not contain any Odoo module.\nPlease start this command "
                "in your project's directory or use `--path` argument" % project_path)

        if not args.db_name:
            # Use the module's name if only one module found else the name of parent folder
            args.db_name = mods[0] if len(mods) == 1 else project_path.split(os.path.sep)[-1]
            # TODO: forbid some database names ? eg template1, ...
            try:
                _create_empty_database(args.db_name)
            except DatabaseExists, e:
                pass
            except Exception, e:
                die("Could not create database `%s`. (%s)" % (args.db_name, e))
            cmdargs.extend(('-d', args.db_name))

        if '--addons-path' not in cmdargs:
            cmdargs.append('--addons-path=%s' % project_path)
        if '--db-filter' not in cmdargs:
            cmdargs.append('--db-filter=^%s$' % args.db_name)
        # if '-i' not in cmdargs and '--init' not in cmdargs:
        #     # Install all modules of projects even if already installed
        #     cmdargs.extend(('-i', ','.join(mods)))

        # FIXME: how to redo config ?
        main(cmdargs)

def die(message, code=1):
    print >>sys.stderr, message
    sys.exit(code)
