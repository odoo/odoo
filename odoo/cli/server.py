# ruff: noqa: PLC0415

import logging
import os
from psycopg2.errors import InsufficientPrivilege

import odoo

from . import (
    Command,
    check_root_user,
    check_postgres_user,
    report_configuration,
    touch_pid_file,
 )


_logger = logging.getLogger('odoo')


def export_translation():
    config = odoo.tools.config
    dbname = config['db_name']

    if config["language"]:
        msg = "language %s" % (config["language"],)
    else:
        msg = "new language"
    _logger.info('writing translation file for %s to %s', msg,
        config["translate_out"])

    fileformat = os.path.splitext(config["translate_out"])[-1][1:].lower()
    # .pot is the same fileformat as .po
    if fileformat == "pot":
        fileformat = "po"

    with open(config["translate_out"], "wb") as buf:
        registry = odoo.modules.registry.Registry.new(dbname)
        with registry.cursor() as cr:
            odoo.tools.translate.trans_export(config["language"],
                config["translate_modules"] or ["all"], buf, fileformat, cr)

    _logger.info('translation file written successfully')


def import_translation():
    config = odoo.tools.config
    overwrite = config["overwrite_existing_translations"]
    dbname = config['db_name']

    registry = odoo.modules.registry.Registry.new(dbname)
    with registry.cursor() as cr:
        translation_importer = odoo.tools.translate.TranslationImporter(cr)
        translation_importer.load_file(config["translate_in"], config["language"])
        translation_importer.save(overwrite=overwrite)


class Server(Command):
    """Start the odoo server (default command)"""

    def run(self, args):
        check_root_user()
        odoo.tools.config.parser.prog = self.title
        odoo.tools.config.parse_config(args, setup_logging=True)
        check_postgres_user()
        report_configuration()

        config = odoo.tools.config

        preload = []
        if config['db_name']:
            preload = config['db_name'].split(',')
            for db_name in preload:
                try:
                    odoo.service.db._create_empty_database(db_name)
                    config['init']['base'] = True
                except InsufficientPrivilege as err:
                    # We use an INFO loglevel on purpose in order to avoid
                    # reporting unnecessary warnings on build environment
                    # using restricted database access.
                    _logger.info("Could not determine if database %s exists, "
                                 "skipping auto-creation: %s", db_name, err)
                except odoo.service.db.DatabaseExists:
                    pass

        if config["translate_out"]:
            export_translation()
            self.exit(0)

        if config["translate_in"]:
            import_translation()
            self.exit(0)

        stop = config["stop_after_init"]

        touch_pid_file()
        rc = odoo.service.server.start(preload=preload, stop=stop)
        self.exit(rc)
