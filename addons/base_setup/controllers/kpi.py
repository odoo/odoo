import logging
from functools import cache
from importlib import import_module

import psycopg2

from odoo.exceptions import ValidationError
from odoo.http import Controller, route
from odoo.modules import Manifest
from odoo.modules import module as odoo_modules_module
from odoo.release import series as release_series
from odoo.sql_db import db_connect
from odoo.tools import SQL

from odoo.addons.base.models.res_users import _check_apikey_credentials

_logger = logging.getLogger(__name__)


@cache  # no need to call more than once per worker
def _get_kpi_providers():
    """
    Load KPI provider functions declared by addons from the addons path.

    This function scans all addon manifests for a ``kpi_providers`` entry,
    expected as a list of strings in the format ``'module.path:function'``,
    where `module.path` is relative to the addon and may be empty (':function').

    :returns: A (cached) tuple of (addon_name, kpi_provider_str, kpi_provider_fn) tuples.
              Only valid and callable functions are returned. Invalid entries are logged.
    :rtype: tuple[tuple]
    """
    kpi_providers = []
    for manifest in Manifest.all_addon_manifests():
        if not manifest:
            continue
        # kpi_providers should be a list of strings in the form 'pkg.module:function'
        # where 'pkg.module' is relative to the addon and can be empty
        for kpi_provider in manifest.get('kpi_providers', []):
            module_path, colon, function = kpi_provider.partition(':')
            if module_path.startswith('.') or not colon:
                _logger.warning(
                    "Invalid KPI provider hook path %r in addon %r. "
                    "Expected formats are 'pkg.module:function' or ':function'.",
                    kpi_provider,
                    manifest.name,
                )
                continue

            try:
                if module_path:
                    # Support "submodule.path:function"
                    module = import_module(f'.{module_path}', package=f'odoo.addons.{manifest.name}')
                else:
                    # Support ":function" for root-level function
                    module = import_module(f'odoo.addons.{manifest.name}')
                if not function:
                    _logger.warning('KPI provider %r from addon %r has an empty function name.', kpi_provider, manifest.name)
                    continue
                fn = getattr(module, function)
            except Exception:
                _logger.exception('Failed to import KPI provider %r from addon %r.', kpi_provider, manifest.name)
                continue

            if not callable(fn):
                _logger.warning('KPI provider %r from addon %r is not callable.', kpi_provider, manifest.name)
                continue

            kpi_providers.append((manifest.name, kpi_provider, fn))

    return tuple(kpi_providers)


def _db_kpi_summary(database, api_key):
    """
    Retrieve the KPI summary from a single database.

    This function connects to the given database, verifies the API key,
    ensures the database version matches the current Odoo release, and
    calls all registered KPI providers.

    :param str database: The name of the database
    :param str api_key:  The API key of a user
    :returns:            Either a dictionary with 'database_version', 'users', 'kpi_summary' and 'errors',
                         or None if the database should be ignored (missing, version mismatch, or invalid key).
    :rtype: dict|None
    """
    try:
        cursor = db_connect(database).cursor()
    except psycopg2.Error:
        # Avoid leaking information about missing database to prevent scanning databases hosted on the same server
        return

    with cursor as cr:
        cr.execute(SQL("SELECT latest_version FROM ir_module_module WHERE name = 'base'"))
        db_version, = cr.fetchone()
        if not db_version.startswith(release_series):
            _logger.error("database %r has version %r that doesn't match running version %r",
                          database, db_version, release_series)
            return  # behave as if the database does not exist

        uid = _check_apikey_credentials(cr, scope='rpc', key=api_key)
        if not uid:
            _logger.error("invalid api key for database %r", database)
            return  # behave as if the database does not exist

        errors = []
        kpi_summary = []
        for addon, kpi_provider, get_kpi_summary in _get_kpi_providers():
            try:
                kpi_summary.extend(get_kpi_summary(cr, uid))
            except Exception:  # noqa: BLE001
                message = f"get_kpi_summary error in addon {addon!r}, provider {kpi_provider!r}"
                _logger.exception(message)
                errors.append({
                    'addon': addon,
                    'kpi_provider': kpi_provider,
                    'message': message,
                })
            finally:
                # get_kpi_summary functions are not expected to have any side effect
                # this also avoids leaving the cursor in a failed transaction state.
                if not odoo_modules_module.current_test:
                    cr.rollback()

        cr.execute(SQL("""
            SELECT u.id,
                   p.name,
                   u.login,
                   (SELECT MAX(create_date)
                      FROM res_users_log log
                      WHERE log.create_uid = u.id) login_date
              FROM res_users u
              JOIN res_partner p ON u.partner_id = p.id
             WHERE u.active
               AND not u.share
        """))
        users = cr.dictfetchall()

        return {
            'database_version': release_series,
            'kpi_summary': kpi_summary,
            'users': users,
            'errors': errors,
        }


class KpiController(Controller):
    @route('/kpi/summary', type='jsonrpc', auth='none', save_session=False)
    def kpi_summary(self, credentials):
        """
        Retrieve the KPI summaries from a batch of databases hosted on the same server.
        The result of this call will only include the databases:
            - that have been found on this server
            - where the provided API key could be verified
            - that are on the same Odoo version as the current Odoo

        Databases that don't match one of these points won't be included in the result,
        and should be contacted separately via RPC calls.

        :param credentials: a list of [db_name, api_key] pairs
        :return A dictionary with db_name as keys and as value a dictionary with keys 'database_version', 'users',
                'kpi_summary' and 'errors', where 'errors' is a list of dictionaries with keys 'addon', 'kpi_provider'
                and 'message'.
        """
        if len(credentials) > 500:
            raise ValidationError("Too many credentials")  # pylint: disable=E8507 # No auth -> no known language to translate to

        result = {}
        for database, api_key in credentials:
            try:
                db_result = _db_kpi_summary(database, api_key)
                if db_result is not None:
                    result[database] = db_result
            except Exception:  # noqa: BLE001
                _logger.exception("get_kpi_summary error")
        return result
