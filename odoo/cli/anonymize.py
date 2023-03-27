# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import optparse
import sys

import odoo

from . import Command

_logger = logging.getLogger(__name__)


class Anonymize(Command):
    """Anonymize a database"""

    def run(self, args):
        parser = odoo.tools.config.parser
        group = optparse.OptionGroup(parser, "Anonymize", "Anonymize the database specified by the `-d` argument.")
        group.add_option("--stdout", action="store_true", dest="to_stdout",
                         help="Output the anonymization SQL instead of applying it")
        parser.add_option_group(group)
        opt = odoo.tools.config.parse_config(args)

        dbname = odoo.tools.config['db_name']
        if not dbname:
            _logger.error('Anonymize command needs a database name. Use "-d" argument')
            sys.exit(1)

        if not opt.to_stdout:
            _logger.info("Starting %s database anonymization", dbname)

        try:
            with odoo.sql_db.db_connect(dbname).cursor() as cursor:
                installed_modules = odoo.modules.anonymize.get_installed_modules(cursor)
                queries = odoo.modules.anonymize.get_anonymization_queries(installed_modules)
                if opt.to_stdout:
                    # pylint: disable=bad-builtin
                    print('BEGIN;')
                    for query in queries:
                        # pylint: disable=bad-builtin
                        print(query.rstrip(";") + ";")
                    # pylint: disable=bad-builtin
                    print("COMMIT;")
                else:
                    for query in queries:
                        cursor.execute(query)
                    _logger.info("Anonymization finished")
        except Exception:
            _logger.critical("An error occurred during the anonymization. THE DATABASE IS NOT ANONYMIZED!")
            sys.exit(1)
