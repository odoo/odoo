#!/usr/bin/env python3

# set server timezone in UTC before time module imported
import os
import logging

import odoo
from odoo.service.server import load_server_wide_modules
from odoo.modules import initialize_sys_path
from odoo.modules.registry import Registry

logging.getLogger().addHandler(logging.StreamHandler())
_logger = logging.getLogger(__name__)

os.environ['TZ'] = 'UTC'
config = odoo.tools.config
# Heroku Postgres url takes the following structure
DATABASE_URL = "postgres://postgres:postgres@localhost:5432/rd-demo"
DATABASE_URL = os.environ.get('DATABASE_URL', DATABASE_URL)

d = DATABASE_URL.split(":")
config['db_user'] = d[1][2:]
config['db_password'] = d[2].split("@")[0]
config['db_host'] = d[2].split("@")[1]
config['db_port'] = d[3].split("/")[0]
config['db_name'] = d[3].split("/")[1]

config['addons_path'] = "addons"
config['heroku_platform'] = True
config['init']['base'] = True


def initialize():

    initialize_sys_path()
    load_server_wide_modules()
    _logger.warning("Starting database initialization")

    update_module = config['init'] or config['update']
    registry = Registry.new(config['db_name'], update_module=update_module)
    _logger.warning("Finished database initialization")


if __name__ == "__main__":
    initialize()