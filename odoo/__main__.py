# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# /odoo/__init__.py is automatically executed first
import odoo.config
import odoo.cli

entrypoints = {
    'server': odoo.cli.server.main,
}

entrypoints[odoo.config.subcommand]()
