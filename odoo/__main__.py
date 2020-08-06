# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import sys
import odoo.bootstrap
odoo.bootstrap.setup(argv=sys.argv[1:])

import odoo.cli
import odoo.config
import odoo.logging_config

odoo.logging_config.init_logger()

entrypoints = {
    'server': odoo.cli.server.main,
    'populate': odoo.cli.populate.main,
    'cloc': odoo.cli.cloc.main,
    'deploy': odoo.cli.cloc.main,
}

entrypoints[odoo.config.subcommand]()
