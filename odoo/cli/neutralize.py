import logging
import sys

import odoo.db
import odoo.modules.neutralize
from odoo.tools import config

from . import Command, get_single_database
from .command import build_config_args

_logger = logging.getLogger(__name__)


class Neutralize(Command):
    """Neutralize a production database for testing: no emails sent, etc."""

    def run(self, args):
        parser = self.parser
        self.add_config_arguments(parser)
        parser.add_argument(
            "--stdout",
            action="store_true",
            dest="to_stdout",
            help="Output the neutralization SQL instead of applying it",
        )
        parsed_args = parser.parse_args(args)

        config_args = build_config_args(parsed_args.config, parsed_args.db_name)
        config.parse_config(config_args, setup_logging=True)

        dbname = get_single_database(config["db_name"])

        if not parsed_args.to_stdout:
            _logger.info("Starting %s database neutralization", dbname)

        try:
            with odoo.db.db_connect(dbname).cursor() as cursor:
                if parsed_args.to_stdout:
                    installed_modules = odoo.modules.neutralize.get_installed_modules(
                        cursor
                    )
                    queries = odoo.modules.neutralize.get_neutralization_queries(
                        installed_modules
                    )
                    print("BEGIN;")
                    for query in queries:
                        print(query.rstrip(";") + ";")
                    print("COMMIT;")
                else:
                    odoo.modules.neutralize.neutralize_database(cursor)

        except Exception:
            _logger.critical(
                "An error occurred during the neutralization. THE DATABASE IS NOT NEUTRALIZED!"
            )
            sys.exit(1)
