from __future__ import annotations

import logging
import optparse
import os
import sys
import time
from typing import TYPE_CHECKING

from odoo import api
from odoo.cli import Command
from odoo.modules import initialize_sys_path
from odoo.modules.registry import Registry
from odoo.tools import config

if TYPE_CHECKING:
    from ..models.blueprint import Blueprint
    from ..models.session import Session

_logger = logging.getLogger(__name__)


class Populate(Command):
    """Populate an Odoo database with synthetic data using blueprints"""

    def run(self, cmdargs):
        """Parse CLI options, open the target database, and run or resume a session.

        :param list[str] cmdargs: Command-line arguments received after ``populate``.
        """
        self._setup_options()
        config.parse_config(['--no-http'] + cmdargs, setup_logging=True)

        try:
            dbname = self._require_single_db()
        except ValueError as e:
            _logger.critical("%s", e)
            sys.exit(1)

        _logger.info("Connecting to database '%s'...", dbname)
        initialize_sys_path()
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            populate_is_installed = bool(env['ir.module.module'].search_count(
                domain=[('name', '=', 'populate'), ('state', '=', 'installed')],
                limit=1,
            ))
            if not populate_is_installed:
                _logger.critical("The 'populate' module must be installed before running the populate CLI command.")
                sys.exit(1)

            try:
                session = self._create(env) if config['resuming'] is None else self._resume(env)
            except ValueError as e:
                _logger.critical("%s", e)
                sys.exit(1)

            self._execute(session, profile=config['profile'])

    def _setup_options(self):
        """Register populate-specific options on the global Odoo CLI parser."""
        parser = config.parser
        parser.prog = self.prog
        group = optparse.OptionGroup(parser, "Populate Configuration")
        group.add_option(
            '--blueprint', '-b', dest='blueprint',
            help="Full xmlid of the Blueprint to execute, or its name.",
        )
        group.add_option(
            '--seed', dest='seed', type='int', my_default=None,
            help="Seed for the random number generator.",
        )
        group.add_option(
            '--scale', dest='scale', type='float', my_default=1,
            help="Factor by which 'counts' in the blueprint should be scaled.",
        )
        group.add_option(
            '--jobs', '-j', dest='job_runners', type='string', my_default='1',
            help="Number of parallel processes to be used for the populate.\n"
                 "Use 'auto' to use all hardware threads.",
        )
        group.add_option(
            '--resume', dest='resuming', type='int', nargs='?', const=0, my_default=None,
            help="Resume from a previous session.\n"
                 "Use without argument to resume the last session, or provide a session ID.",
        )
        group.add_option(
            '--profile', dest='profile', action='store_true', my_default=False,
            help="Profile populate execution.",
        )
        parser.add_option_group(group)
        config._load_default_options()

    @staticmethod
    def _require_single_db() -> str:
        """Return the single database selected for the populate command.

        :return: Database name passed through ``-d``/``--database``.
        :raise ValueError: If no database or several databases were provided.
        """
        dbnames = config['db_name']
        if not dbnames:
            msg = "Database name is required. Use -d/--database option."
            raise ValueError(msg)
        if len(dbnames) > 1:
            msg = "Multiple databases specified. Please provide a single database."
            raise ValueError(msg)
        return dbnames[0]

    @staticmethod
    def _resolve_blueprint(env: api.Environment) -> Blueprint:
        """Resolve the configured blueprint from an XML id or a blueprint name.

        :param env: Environment connected to the target database.
        :return: Singleton ``populate.blueprint`` record to execute.
        :raise ValueError: If no blueprint is configured, missing, or ambiguous.
        """
        name = config['blueprint']
        if not name:
            msg = "Blueprint is required. Use -b/--blueprint option."
            raise ValueError(msg)

        blueprint = env.ref(name, raise_if_not_found=False)
        if not blueprint:
            blueprint = env['populate.blueprint'].search([('name', '=', name)])

        if not blueprint:
            raise ValueError(
                f"Blueprint '{name}' was not found in the database. "
                "Please double check the name, and make sure the relevant module is installed. "
                "If you just installed it, upgrade the 'populate' module to load its' blueprints."  # noqa: COM812
            )
        if len(blueprint) > 1:
            raise ValueError(
                f"Multiple blueprints found with name '{name}'. "
                f"Please specify the fully qualified xmlid."  # noqa: COM812
            )
        return blueprint

    @staticmethod
    def _create(env: api.Environment) -> Session:
        """Create and commit a new populate session from the configured options.

        The commit makes the session visible to worker processes and allows it to
        be resumed if the command is interrupted before execution finishes.

        :param env: Environment connected to the target database.
        :return: Newly created ``populate.session`` record.
        """
        blueprint = Populate._resolve_blueprint(env)
        worker_count = (
            os.cpu_count()
            if config['job_runners'] == 'auto'
            else int(config['job_runners'])
        )
        vals = {
            'blueprint_id': blueprint.id,
            'worker_count': worker_count,
            'scaling_factor': config['scale'],
        }
        if (seed := config['seed']) is not None:
            vals['seed'] = seed

        session = env['populate.session'].create(vals)

        _logger.info("Created populate session %d", session.id)
        # Commit the newly created session,
        # so it can be resumed or used in multiprocess mode.
        session.env.cr.commit()
        return session

    @staticmethod
    def _resume(env: api.Environment) -> Session:
        """Find the session requested by ``--resume``.

        Without an explicit id, the latest unfinished session is selected.

        :param env: Environment connected to the target database.
        :return: Existing unfinished ``populate.session`` record.
        :raise ValueError: If no resumable session exists.
        """
        session_id = config['resuming']
        if session_id:
            session = env['populate.session'].browse(session_id)
        else:
            session = env['populate.session'].search(
                domain=[('job_ids.is_done', '=', False)],
                order='id desc',
                limit=1,
            )

        if not session.exists():
            msg = "No session found to resume."
            raise ValueError(msg)

        _logger.info("Resuming populate session %d", session.id)
        return session

    @staticmethod
    def _execute(session: Session, *, profile: bool = False):
        """Run a session and translate runtime failures to CLI exit codes.

        :param session: Session to execute or resume.
        :param profile: Whether to save profiler entries for this invocation.
        """
        from odoo.addons.populate import start_populate  # noqa: PLC0415

        time_start = time.time()
        try:
            start_populate(session, profile=profile)
        except KeyboardInterrupt:
            session.env.cr.rollback()
            _logger.info("Interrupted populate session %d. Resume later with `--resume`.", session.id)
            sys.exit(0)
        except Exception:
            session.env.cr.rollback()
            _logger.exception("Failed to execute blueprint '%s'", session.blueprint_id.name)
            sys.exit(1)

        duration = Populate._format_duration(time.time() - time_start)
        _logger.info("Blueprint '%s' executed successfully in %s", session.blueprint_id.name, duration)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {secs:.3f}s"

        if minutes > 0:
            return f"{int(minutes)}m {secs:.3f}s"

        return f"{secs:.3f}s"
