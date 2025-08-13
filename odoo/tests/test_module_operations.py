#!/usr/bin/env python3
import argparse
import logging.config
import os
import sys
import threading
import time

sys.path.append(os.path.abspath(os.path.join(__file__,'../../../')))

import odoo
from odoo.tools import config, topological_sort, unique
from odoo.netsvc import init_logger
from odoo.tests import standalone_tests
import odoo.tests.loader

_logger = logging.getLogger('odoo.tests.test_module_operations')

BLACKLIST = {
    'auth_ldap',
    'pos_blackbox_be',
}
IGNORE = ('hw_', 'theme_', 'l10n_', 'test_')

INSTALL_BLACKLIST = {
    'payment_alipay', 'payment_ogone', 'payment_payulatam', 'payment_payumoney',
}  # deprecated modules (cannot be installed manually through button_install anymore)

def install(db_name, module_id, module_name):
    with odoo.registry(db_name).cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        module = env['ir.module.module'].browse(module_id)
        module.button_immediate_install()
    _logger.info('%s installed', module_name)


def uninstall(db_name, module_id, module_name):
    with odoo.registry(db_name).cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        module = env['ir.module.module'].browse(module_id)
        module.button_immediate_uninstall()
    _logger.info('%s uninstalled', module_name)


def cycle(db_name, module_id, module_name):
    install(db_name, module_id, module_name)
    uninstall(db_name, module_id, module_name)
    install(db_name, module_id, module_name)


class CheckAddons(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        self.values = namespace
        config._check_addons_path(self, option_string, values, self)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Script for testing the install / uninstall / reinstall"
                    " cycle of Odoo modules. Prefer the 'cycle' subcommand to"
                    " running this without anything specified (this is the"
                    " default behaviour).")
    parser.set_defaults(
        func=test_cycle,
        reinstall=True,
    )
    fake_commands = parser.add_mutually_exclusive_group()

    parser.add_argument("--database", "-d", type=str, required=True,
        help="The database to test (/ run the command on)")
    parser.add_argument("--data-dir", "-D", dest="data_dir", type=str,
        help="Directory where to store Odoo data"
    )
    parser.add_argument("--skip", "-s", type=str,
        help="Comma-separated list of modules to skip (they will only be installed)")
    parser.add_argument("--resume-at", "-r", type=str,
        help="Skip modules (only install) up to the specified one in topological order")
    parser.add_argument("--addons-path", "-p", type=str, action=CheckAddons,
        help="Comma-separated list of paths to directories containing extra Odoo modules")

    cmds = parser.add_subparsers(title="subcommands", metavar='')
    cycle = cmds.add_parser(
        'cycle', help="Full install/uninstall/reinstall cycle.",
        description="Installs, uninstalls, and reinstalls all modules which are"
                    " not skipped or blacklisted, the database should have"
                    " 'base' installed (only).")
    cycle.set_defaults(func=test_cycle)

    fake_commands.add_argument(
        "--uninstall", "-U", action=UninstallAction,
        help="Comma-separated list of modules to uninstall/reinstall. Prefer the 'uninstall' subcommand."
    )
    uninstall = cmds.add_parser(
        'uninstall', help="Uninstallation",
        description="Uninstalls then (by default) reinstalls every specified "
                    "module. Modules which are not installed before running "
                    "are ignored.")
    uninstall.set_defaults(func=test_uninstall)
    uninstall.add_argument('uninstall', help="comma-separated list of modules to uninstall/reinstall")
    uninstall.add_argument(
        '-n', '--no-reinstall', dest='reinstall', action='store_false',
        help="Skips reinstalling the module(s) after uninstalling."
    )

    fake_commands.add_argument("--standalone", action=StandaloneAction,
        help="Launch standalone scripts tagged with @standalone. Accepts a list of "
             "module names or tags separated by commas. 'all' will run all available scripts. Prefer the 'standalone' subcommand."
    )
    standalone = cmds.add_parser('standalone', help="Run scripts tagged with @standalone")
    standalone.set_defaults(func=test_standalone)
    standalone.add_argument('standalone', help="List of module names or tags separated by commas, 'all' will run all available scripts.")

    return parser.parse_args()

class UninstallAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        namespace.func = test_uninstall
        setattr(namespace, self.dest, values)

class StandaloneAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        namespace.func = test_standalone
        setattr(namespace, self.dest, values)

def test_cycle(args):
    """ Test full install/uninstall/reinstall cycle for all modules """
    with odoo.registry(args.database).cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

        def valid(module):
            return not (
                module.name in BLACKLIST
                or module.name in INSTALL_BLACKLIST
                or module.name.startswith(IGNORE)
                or module.state in ('installed', 'uninstallable')
            )

        modules = env['ir.module.module'].search([]).filtered(valid)

        # order modules in topological order
        modules = modules.browse(topological_sort({
            module.id: module.dependencies_id.depend_id.ids
            for module in modules
        }))
        modules_todo = [(module.id, module.name) for module in modules]

    resume = args.resume_at
    skip = set(args.skip.split(',')) if args.skip else set()
    for module_id, module_name in modules_todo:
        if module_name == resume:
            resume = None

        if resume or module_name in skip:
            install(args.database, module_id, module_name)
        else:
            cycle(args.database, module_id, module_name)


def test_uninstall(args):
    """ Tries to uninstall/reinstall one ore more modules"""
    for module_name in args.uninstall.split(','):
        with odoo.registry(args.database).cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            module = env['ir.module.module'].search([('name', '=', module_name)])
            module_id, module_state = module.id, module.state

        if module_state == 'installed':
            uninstall(args.database, module_id, module_name)
            if args.reinstall and module_name not in INSTALL_BLACKLIST:
                install(args.database, module_id, module_name)
        elif module_state:
            _logger.warning("Module %r is not installed", module_name)
        else:
            _logger.warning("Module %r does not exist", module_name)


def test_standalone(args):
    """ Tries to launch standalone scripts tagged with @post_testing """
    # load the registry once for script discovery
    registry = odoo.registry(args.database)
    for module_name in registry._init_modules:
        # import tests for loaded modules
        odoo.tests.loader.get_test_modules(module_name)

    # fetch and filter scripts to test
    funcs = list(unique(
        func
        for tag in args.standalone.split(',')
        for func in standalone_tests[tag]
    ))

    start_time = time.time()
    for index, func in enumerate(funcs, start=1):
        with odoo.registry(args.database).cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            _logger.info("Executing standalone script: %s (%d / %d)",
                         func.__name__, index, len(funcs))
            try:
                func(env)
            except Exception:
                _logger.error("Standalone script %s failed", func.__name__, exc_info=True)

    _logger.info("%d standalone scripts executed in %.2fs", len(funcs), time.time() - start_time)


if __name__ == '__main__':
    args = parse_args()

    config['db_name'] = threading.current_thread().dbname = args.database
    # handle paths option
    if args.addons_path:
        odoo.tools.config['addons_path'] = ','.join([args.addons_path, odoo.tools.config['addons_path']])
        if args.data_dir:
            odoo.tools.config['data_dir'] = args.data_dir
        odoo.modules.module.initialize_sys_path()

    init_logger()
    logging.config.dictConfig({
        'version': 1,
        'incremental': True,
        'disable_existing_loggers': False,
        'loggers': {
            'odoo.modules.loading': {'level': 'CRITICAL'},
            'odoo.sql_db': {'level': 'CRITICAL'},
            'odoo.models.unlink': {'level': 'WARNING'},
            'odoo.addons.base.models.ir_model': {'level': "WARNING"},
        }
    })

    try:
        args.func(args)
    except Exception:
        _logger.error("%s tests failed", args.func.__name__[5:])
        raise
