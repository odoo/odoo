# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import optparse
import sys

import odoo

from pathlib import Path

from . import Command

_logger = logging.getLogger(__name__)


class Neutralize(Command):
    """neutralize a database"""

    def run(self, args):
        parser = odoo.tools.config.parser
        group = optparse.OptionGroup(parser, "Neutralize", "Neutralize the database specified by the `-d` argument.")
        parser.add_option_group(group)
        odoo.tools.config.parse_config(args)

        dbname = odoo.tools.config['db_name']
        if not dbname:
            _logger.error('Neutralize command needs a database name. Use "-d" argument')
            sys.exit(1)

        registry = odoo.registry(dbname)
        _logger.info('Starting database neutralization')
        try:
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                for model in env.values():
                    model._neutralize()
                env['ir.config_parameter'].set_param('database.is_neutralized', True)
                # Signal changes so the config parameter we just set gets updated in a
                # running database without requiring a restart.
                env.registry.signal_changes()
                with open(Path(__file__).parent / 'neutralize_watermarks.xml', 'rb') as f:
                    odoo.tools.convert_xml_import(cr, "__neutralize__", f)
        except Exception:
            _logger.error('An exception occured during neutralization.')
            raise
        _logger.info('Neutralization finished')
