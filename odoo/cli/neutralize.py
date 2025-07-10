import logging
import sys

import odoo.modules.neutralize
import odoo.sql_db
from odoo.modules.registry import Registry
from odoo.tools import config

from . import Command

_logger = logging.getLogger(__name__)


class Neutralize(Command):
    """Neutralize a production database for testing: no emails sent, etc."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        self.parser.add_argument(
            "--stdout", action="store_true",
            help="Dry run: output the neutralization SQL to stdout instead of applying it")

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = []
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]

        config.parse_config(config_args, setup_logging=True)

        if not parsed_args.stdout:
            _logger.info("Starting %s database neutralization", parsed_args.db_name)

        try:
            with Registry(parsed_args.db_name).cursor() as cr:
                if parsed_args.stdout:
                    installed_modules = odoo.modules.neutralize.get_installed_modules(cr)
                    queries = odoo.modules.neutralize.get_neutralization_queries(installed_modules)
                    print('BEGIN;')  # noqa: T201
                    for query in queries:
                        print(query.rstrip(";") + ";")   # noqa: T201
                    print("COMMIT;")   # noqa: T201
                else:
                    odoo.modules.neutralize.neutralize_database(cr)
        except Exception:  # noqa: BLE001
            _logger.critical("An error occurred during the neutralization. THE DATABASE IS NOT NEUTRALIZED!")
            sys.exit(1)
