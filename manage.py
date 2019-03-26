#!/usr/bin/env python
# -*- coding: utf-8 -*-

import code
import logging
import os
from argparse import ArgumentParser
from pprint import pprint as pp

import openerp
from openerp import SUPERUSER_ID

logger = logging.getLogger('openerp.manage')

DEFAULT_OPENERP_CONF = '/srv/openerp-server.conf'


def start_bootstrap(dbname, config_path=None):
    """
    Heavily copy/paste from default openerp-server script.
    """
    os.environ["TZ"] = "UTC"

    conf_args = ['--debug']  # Maybe useless?

    conf_args.append('-c')
    if config_path:
        conf_args.append(config_path)
    else:
        # Assume a default one to be sure to load custom modules with models...
        if not os.path.exists(DEFAULT_OPENERP_CONF):
            raise Exception(
                'Missing openerp-server.conf file. Trying with {} but doesn\'t exists...'.format(DEFAULT_OPENERP_CONF))

        conf_args.append(DEFAULT_OPENERP_CONF)

    # Init config and logger.
    openerp.tools.config.parse_config(conf_args)
    openerp.netsvc.init_logger()

    # Then bootstrap every modules.
    for mod in openerp.conf.server_wide_modules:
        try:
            openerp.modules.module.load_openerp_module(mod)
        except Exception:
            logger.exception('Failed to load server-wide module `%s`.%s', mod)

    # Get the most important things: DB cursor and registry (pooler) !!
    db, pool = openerp.pooler.get_db_and_pool(dbname, pooljobs=False)
    cr = db.cursor()
    cr.autocommit(True)

    return db, cr, pool


def end_bootstrap(cr):
    cr.close()
    logging.shutdown()


def shell_subcommand(args):
    locals = {
        'cr': cr,
        'pool': pool,
        'uid': SUPERUSER_ID,
        'pp': pp,
    }
    banner = """
    Welcome to the OpenERP shell! Well, this is not Django but we try to make it better!

    Available global variables: %s

    Example usage:
    >>> user_obj = pool.get('res.users')
    >>> user_obj.write(cr, uid, 1, {'name': 'Jean Jass'})
    >>> user_obj.browse(cr, uid, 1).name == 'Jean Jass'
                    """ % ('\n- ' + '\n- '.join(locals.keys()))

    code.interact(banner=banner, local=locals)


def migrate_subcommand(args):
    module = args.module
    version = '{}.{}'.format(openerp.release.major_version, args.version)

    cr.execute("""
           SELECT latest_version
           FROM ir_module_module
           WHERE name = %s
       """, (module,))
    current_version = cr.fetchone()[0]

    # Force installed version and state
    cr.execute("""
        UPDATE ir_module_module
        SET latest_version = %s, state = %s
        WHERE name = %s
    """, (version, 'to upgrade', module))

    # Needs to load all dependencies (of dependencies) and for this, much easier
    # to load all modules installed...
    cr.execute("SELECT name from ir_module_module WHERE state IN %s" ,(tuple(['installed', 'to upgrade']),))
    module_list = [name for (name,) in cr.fetchall()]

    graph = openerp.modules.graph.Graph()
    graph.add_modules(cr, module_list, force=[module])
    package = graph.get(module)  # Got our node graph.

    migrate_manager = openerp.modules.migration.MigrationManager(cr, graph)

    try:
        migrate_manager.migrate_module(package, args.stage)
    except Exception as exc:
        cr.execute("""
            UPDATE ir_module_module
            SET latest_version = %s, state = %s
            WHERE name = %s
        """, (current_version, 'installed', module))
        raise exc
    else:
        # Yes, the above method don't do this... We have to do it manually!
        latest_version = '{}.{}'.format(openerp.release.major_version, package.data['version'])
        cr.execute("""
            UPDATE ir_module_module
            SET latest_version = %s, state = %s
            WHERE name = %s
        """, (latest_version, 'installed', module))


def password_reset_subcommand(args):
    user_obj = pool.get('res.users')

    # Note: login is supposed to be unique (by default at least!).
    user_ids = user_obj.search(cr, SUPERUSER_ID, [('login', '=', args.login)])
    if user_ids:
        # On update, base_crypt module field callback is executed if enabled (NOT for creation).
        user_obj.write(cr, SUPERUSER_ID, user_ids, {'password': args.new_password})
        logger.info('The user {} has its password updated'.format(args.login))
    else:
        logger.warning('No user match for login {}'.format(args.login))


def anonymize_subcommand(args):
    user_obj = pool.get('res.users')
    address_obj = pool.get('res.partner.address')
    fetchmail_obj = pool.get('fetchmail.server')

    # Pfffiou, loads all users... RIP postgreSQL and Python memory!!
    # Of course, maybe better to make a batch for this but no more time yet :/
    # Afterall, this is just a huge list of ID's ;-)
    user_ids = user_obj.search(cr, SUPERUSER_ID, [])
    if user_ids:
        user_obj.write(cr, SUPERUSER_ID, user_ids, {
            'password': args.new_password,  # Use API for specific salt, etc.
            'email': args.new_email,
        })
        logger.info('All users have their passwords and emails updated')

    if address_obj:
        addresses_ids = address_obj.search(cr, SUPERUSER_ID, [])
        if addresses_ids:
            address_obj.write(cr, SUPERUSER_ID, addresses_ids, {'email': args.new_email})
            logger.info('All partner addresses email have been reset.')

    if fetchmail_obj:
        server_ids = fetchmail_obj.search(cr, SUPERUSER_ID, [])
        if server_ids:
            fetchmail_obj.write(cr, SUPERUSER_ID, server_ids, {'password': ''})
            logger.info('Fetchmail server conf reset.')


COMMAND_SHELL = 'shell'
COMMAND_MIGRATE = 'migrate'
COMMAND_PASSWORD_RESET = 'password_reset'
COMMAND_ANONYMIZE = 'anonymize'
COMMANDS = [
    COMMAND_SHELL,
    COMMAND_MIGRATE,
    COMMAND_PASSWORD_RESET,
    COMMAND_ANONYMIZE,
]

MIGRATE_STAGE_PRE = 'pre'
MIGRATE_STAGE_POST = 'post'
MIGRATE_STAGES = [
    MIGRATE_STAGE_PRE,
    MIGRATE_STAGE_POST,
]
MIGRATE_STAGE_DEFAULT = 'post'

parser = ArgumentParser()
parser.add_argument('-d', dest='dbname', required=True, help="REQUIRED: The database to execute against.")
parser.add_argument('-c', dest='config_path', help="The config file to use.")
subparsers = parser.add_subparsers(help='Available sub-commands are:\n-{}'.format('\n-'.join(COMMANDS)))

parser_shell = subparsers.add_parser(COMMAND_SHELL, help='Start an interactive shell with an OpenERP bootstraped.')
parser_shell.set_defaults(func=shell_subcommand)

parser_migrate = subparsers.add_parser(
    COMMAND_MIGRATE,
    help='Alternative way to update modules. Better for debugging ONLY (no thread).',
)
parser_migrate.set_defaults(func=migrate_subcommand)
parser_migrate.add_argument('module')
parser_migrate.add_argument(
    'version',
    help='The previous version to force. For example, if the current '
         'version is 2.11.2, you must enter 2.11.1 to play the migration 2.11.2'
         '**ONLY**. Be careful, the migrations are not undo (OpenERP don\'t'
         'implement it!)',
)
parser_migrate.add_argument(
    '--stage',
    default=MIGRATE_STAGE_DEFAULT,
    choices=MIGRATE_STAGES,
    help='The migration stage to apply. Possible values: {}. Default to {}.'.format(
        ','.join(MIGRATE_STAGES),
        MIGRATE_STAGE_DEFAULT,
    ),
)

parser_pass_reset = subparsers.add_parser(COMMAND_PASSWORD_RESET, help='Reset the password of the given user (by filtering on (unique) login).')
parser_pass_reset.set_defaults(func=password_reset_subcommand)
parser_pass_reset.add_argument('--login', required=True)
parser_pass_reset.add_argument('--new-password', required=True)

parser_anonymize = subparsers.add_parser(COMMAND_ANONYMIZE, help='Reset ALL users password and email.')
parser_anonymize.set_defaults(func=anonymize_subcommand)
parser_anonymize.add_argument('--new-password', required=True)
parser_anonymize.add_argument('--new-email', required=True)

if __name__ == "__main__":
    args = parser.parse_args()
    db, cr, pool = start_bootstrap(args.dbname, args.config_path)

    try:
        args.func(args)
    finally:
        end_bootstrap(cr)
