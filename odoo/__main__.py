# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# /odoo/__init__.py is automatically executed first
import odoo.bootstrap
import odoo.config
import odoo.cli

odoo.bootstrap.boot(aslib=False)

entrypoints = {
    'server': odoo.cli.server.main,
    'populate': odoo.cli.populate.Populate().run
}

entrypoints[odoo.config.subcommand]()
