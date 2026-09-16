import logging
import sys

import odoo.db
import odoo.modules.neutralize
from odoo.libs.debug_log import DebugLog

from . import DatabaseCommand

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class Neutralize(DatabaseCommand):
    description = "Neutralize a production database for testing: no emails sent, etc."

    def __init__(self) -> None:
        super().__init__()
        self.add_config_arguments(self.parser)
        self.parser.add_argument(
            "--stdout",
            action="store_true",
            dest="to_stdout",
            help="Output the neutralization SQL instead of applying it",
        )

    def run(self, args: list[str]) -> None:
        parsed_args, unknown = self.parse_args(args)
        dbname = self.bootstrap_config(parsed_args, extra_args=unknown)

        _logger.info("Starting %s database neutralization", dbname)
        _debug.lifecycle("cli.neutralize", db=dbname, to_stdout=parsed_args.to_stdout)
        if parsed_args.to_stdout:
            self._print_neutralization_queries(dbname)
        else:
            neutralize_database_or_exit(dbname)
        _debug.lifecycle(
            "cli.neutralize.done",
            db=dbname,
            mode="printed" if parsed_args.to_stdout else "applied",
        )

    @staticmethod
    def _print_neutralization_queries(dbname: str) -> None:
        with odoo.db.db_connect(dbname).cursor() as cursor:
            with _debug.perf(
                "cli.neutralize.installed_modules", cr=cursor, db=dbname
            ) as span:
                installed_modules = odoo.modules.neutralize.get_installed_module_names(
                    cursor
                )
                span.set(modules=len(installed_modules))
            queries = odoo.modules.neutralize.get_neutralization_queries(
                installed_modules
            )
        printed = 0  # debuglog
        print("BEGIN;")
        for query in queries:
            print(query.rstrip(";") + ";")
            printed += 1  # debuglog
        print("COMMIT;")
        _debug.logic(
            "cli.neutralize.printed",
            db=dbname,
            modules=len(installed_modules),
            queries=printed,
        )


def neutralize_database_or_exit(dbname: str) -> None:
    try:
        with odoo.db.db_connect(dbname).cursor() as cursor:
            with _debug.perf("cli.neutralize.apply", cr=cursor, db=dbname):
                odoo.modules.neutralize.neutralize_database(cursor)
    except Exception as e:
        _debug.logic("cli.neutralize.failed", db=dbname, error=type(e).__name__)
        _logger.critical(
            "An error occurred during the neutralization. THE DATABASE IS NOT NEUTRALIZED!",
            exc_info=True,
        )
        sys.exit(1)
