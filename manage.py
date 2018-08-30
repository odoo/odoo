#!/usr/bin/env python
# -*- coding: utf-8 -*-

import code
import logging
import os
from argparse import ArgumentParser

import openerp
from openerp import SUPERUSER_ID

logger = logging.getLogger('openerp.manage')

COMMAND_SHELL = 'shell'
COMMANDS = [
    COMMAND_SHELL,
]

parser = ArgumentParser()
parser.add_argument('command', choices=COMMANDS, help="A command to execute. For e.g: {}".format('|'.join(COMMANDS)), )
parser.add_argument('-d', dest='dbname', required=True, help="REQUIRED: The database to execute against.")
parser.add_argument('-c', dest='config_path', help="The config file to use.")


def start_bootstrap(dbname, config_path):
    os.environ["TZ"] = "UTC"

    conf_args = ['--debug']  # Maybe useless?
    if config_path:
        conf_args.append('-c')
        conf_args.append(config_path)

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
    db, pool = openerp.pooler.get_db_and_pool(dbname)
    cr = db.cursor()

    return cr, pool


def end_bootstrap(cr):
    cr.commit()
    cr.close()
    logging.shutdown()
    # openerp.modules.registry.RegistryManager.delete_all()


if __name__ == "__main__":
    args = parser.parse_args()

    cr, pool = start_bootstrap(args.dbname, args.config_path)

    if args.command == 'shell':
        locals = {
            'cr': cr,
            'pool': pool,
            'uid': SUPERUSER_ID,
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

    end_bootstrap(cr)
