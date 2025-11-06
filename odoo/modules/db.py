# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Initialize the database for module management and Odoo installation. """
from __future__ import annotations

import collections
import contextlib
import functools
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import typing
import zipfile
from contextlib import closing, suppress
from datetime import datetime
from enum import IntEnum
from importlib import resources
from zoneinfo import TZPATH

import psycopg2
from psycopg2.extras import Json

import odoo.api
import odoo.modules
import odoo.modules.neutralize
import odoo.release
import odoo.sql_db
import odoo.tools
from odoo.exceptions import AccessDenied, UserError
from odoo.tools import SQL, config, osutil
from odoo.tools.date_utils import all_timezones
from odoo.tools.misc import exec_pg_environ, find_pg_tool
from odoo.tools.sql import quoted_identifier

if typing.TYPE_CHECKING:
    from odoo.sql_db import BaseCursor, Cursor

_logger = logging.getLogger(__name__)

DB_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$')


def is_initialized(cr: Cursor) -> bool:
    """ Check if a database has been initialized for the ORM.

    The database can be initialized with the 'initialize' function below.

    """
    return odoo.tools.sql.table_exists(cr, 'ir_module_module')


def initialize(cr: Cursor) -> None:
    """ Initialize a database with for the ORM.

    This executes base/data/base_data.sql, creates the ir_module_categories
    (taken from each module descriptor file), and creates the ir_module_module
    and ir_model_data entries.

    """
    try:
        f = odoo.tools.misc.file_path('base/data/base_data.sql')
    except FileNotFoundError:
        m = "File not found: 'base.sql' (provided by module 'base')."
        _logger.critical(m)
        raise OSError(m)

    with odoo.tools.misc.file_open(f) as base_sql_file:
        cr.execute(base_sql_file.read())  # pylint: disable=sql-injection

    for info in odoo.modules.Manifest.all_addon_manifests():
        module_name = info.name
        categories = info['category'].split('/')
        category_id = create_categories(cr, categories)

        if info['installable']:
            state = 'uninstalled'
        else:
            state = 'uninstallable'

        cr.execute('INSERT INTO ir_module_module \
                (author, website, name, shortdesc, description, \
                    category_id, auto_install, state, web, license, application, icon, sequence, summary) \
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id', (
            info['author'],
            info['website'], module_name, Json({'en_US': info['name']}),
            Json({'en_US': info['description']}), category_id,
            info['auto_install'] is not False, state,
            info['web'],
            info['license'],
            info['application'], info['icon'],
            info['sequence'], Json({'en_US': info['summary']})))
        row = cr.fetchone()
        assert row is not None  # for typing
        module_id = row[0]
        cr.execute(
            'INSERT INTO ir_model_data'
            '(name,model,module, res_id, noupdate) VALUES (%s,%s,%s,%s,%s)',
            ('module_' + module_name, 'ir.module.module', 'base', module_id, True),
        )
        dependencies = info['depends']
        for d in dependencies:
            cr.execute(
                'INSERT INTO ir_module_module_dependency (module_id, name, auto_install_required)'
                ' VALUES (%s, %s, %s)',
                (module_id, d, d in (info['auto_install'] or ())),
            )

    from odoo.tools import config  # noqa: PLC0415
    if config.get('skip_auto_install'):
        # even if skip_auto_install is enabled we still want to have base
        cr.execute("""UPDATE ir_module_module SET state='to install' WHERE name = 'base'""")
        return

    # Install recursively all auto-installing modules
    while True:
        # this selects all the auto_install modules whose auto_install_required
        # deps are marked as to install
        cr.execute("""
        SELECT m.name FROM ir_module_module m
        WHERE m.auto_install
        AND state not in ('to install', 'uninstallable')
        AND NOT EXISTS (
            SELECT 1 FROM ir_module_module_dependency d
            JOIN ir_module_module mdep ON (d.name = mdep.name)
            WHERE d.module_id = m.id
              AND d.auto_install_required
              AND mdep.state != 'to install'
        )""")
        to_auto_install = [x[0] for x in cr.fetchall()]
        # however if the module has non-required deps we need to install
        # those, so merge-in the modules which have a dependen*t* which is
        # *either* to_install or in to_auto_install and merge it in?
        cr.execute("""
        SELECT d.name FROM ir_module_module_dependency d
        JOIN ir_module_module m ON (d.module_id = m.id)
        JOIN ir_module_module mdep ON (d.name = mdep.name)
        WHERE (m.state = 'to install' OR m.name = any(%s))
            -- don't re-mark marked modules
        AND NOT (mdep.state = 'to install' OR mdep.name = any(%s))
        """, [to_auto_install, to_auto_install])
        to_auto_install.extend(x[0] for x in cr.fetchall())

        if not to_auto_install:
            break
        cr.execute("""UPDATE ir_module_module SET state='to install' WHERE name in %s""", (tuple(to_auto_install),))


def create_categories(cr: Cursor, categories: list[str]) -> int | None:
    """ Create the ir_module_category entries for some categories.

    categories is a list of strings forming a single category with its
    parent categories, like ['Grand Parent', 'Parent', 'Child'].

    Return the database id of the (last) category.

    """
    p_id = None
    category = []
    while categories:
        category.append(categories[0])
        xml_id = 'module_category_' + ('_'.join(x.lower() for x in category)).replace('&', 'and').replace(' ', '_')
        # search via xml_id (because some categories are renamed)
        cr.execute("SELECT res_id FROM ir_model_data WHERE name=%s AND module=%s AND model=%s",
                   (xml_id, "base", "ir.module.category"))

        row = cr.fetchone()
        if not row:
            cr.execute('INSERT INTO ir_module_category \
                    (name, parent_id) \
                    VALUES (%s, %s) RETURNING id', (Json({'en_US': categories[0]}), p_id))
            row = cr.fetchone()
            assert row is not None  # for typing
            p_id = row[0]
            cr.execute('INSERT INTO ir_model_data (module, name, res_id, model, noupdate) \
                       VALUES (%s, %s, %s, %s, %s)', ('base', xml_id, p_id, 'ir.module.category', True))
        else:
            p_id = row[0]
        assert isinstance(p_id, int)
        categories = categories[1:]
    return p_id


class FunctionStatus(IntEnum):
    MISSING = 0  # function is not present (falsy)
    PRESENT = 1  # function is present but not indexable (not immutable)
    INDEXABLE = 2  # function is present and indexable (immutable)


def has_unaccent(cr: BaseCursor) -> FunctionStatus:
    """ Test whether the database has function 'unaccent' and return its status.

    The unaccent is supposed to be provided by the PostgreSQL unaccent contrib
    module but any similar function will be picked by OpenERP.

    :rtype: FunctionStatus
    """
    cr.execute("""
        SELECT p.provolatile
        FROM pg_proc p
            LEFT JOIN pg_catalog.pg_namespace ns ON p.pronamespace = ns.oid
        WHERE p.proname = 'unaccent'
              AND p.pronargs = 1
              AND ns.nspname = 'public'
    """)
    result = cr.fetchone()
    if not result:
        return FunctionStatus.MISSING
    # The `provolatile` of unaccent allows to know whether the unaccent function
    # can be used to create index (it should be 'i' - means immutable), see
    # https://www.postgresql.org/docs/current/catalog-pg-proc.html.
    return FunctionStatus.INDEXABLE if result[0] == 'i' else FunctionStatus.PRESENT


def has_trigram(cr: BaseCursor) -> bool:
    """ Test if the database has the a word_similarity function.

    The word_similarity is supposed to be provided by the PostgreSQL built-in
    pg_trgm module but any similar function will be picked by Odoo.

    """
    cr.execute("SELECT proname FROM pg_proc WHERE proname='word_similarity'")
    return len(cr.fetchall()) > 0


# ----------------------------------------------------------
# Database management
# ----------------------------------------------------------

def verify_db_management_enabled() -> None:
    """
    Verify that the database manager is enabled in the configuration. It
    verifies that ``--no-database-list`` is absent from the CLI and that
    ``list_db=0`` is absent from the odoorc configuration file.
    """
    if not odoo.tools.config['list_db']:
        e = "Database management functions blocked, admin disabled database listing."
        raise AccessDenied(e)


def verify_admin_password(passwd: str) -> None:
    """
    Verify that the admin password matches the one saved in the odoorc
    configuration file. It raises an AccessDenied when the verification
    fails.

    The password can instead be ``odoo.modules.db.SKIP_ADMIN_PASSWORD``
    which is a special flag to bypass the verification.
    """
    if not passwd or not odoo.tools.config.verify_admin_password(passwd):
        e = "Database management function blocked, bad admin password."
        raise AccessDenied(e)


@functools.cache
def country_timezones():
    """Ported from pytz on top of zoneinfo: the mapping of country code is
    available in tzdb's zone.tab (and in a more complex / complete form in
    zone1970.tab but we ignore that), following the example of zoneinfo we first
    check for it in tzdata and fall back on the OS's zoneinfo db.
    """
    zonemap = collections.defaultdict(list)

    tzpath = []
    with contextlib.suppress(ModuleNotFoundError):
        tzpath = [resources.files('tzdata').joinpath('zoneinfo')]
    tzpath.extend(map(pathlib.Path, TZPATH))

    for p in tzpath:
        try:
            zone_file = p.joinpath('zone.tab').open('r', encoding='ascii')
        except FileNotFoundError:
            continue

        with zone_file:
            for line in zone_file:
                if line.startswith('#'):
                    continue
                code, _coordinates, zone = line.split(None, 4)[:3]
                if zone not in all_timezones:
                    continue
                zonemap[code].append(zone)
            break

    return dict(zonemap)


def _check_faketime_mode(db_name: str) -> None:
    if not os.getenv('ODOO_FAKETIME_TEST_MODE'):
        return
    if db_name not in odoo.tools.config['db_name']:
        return
    try:
        db = odoo.sql_db.db_connect(db_name)
        with db.cursor() as cursor:
            cursor.execute("SELECT (pg_catalog.now() AT TIME ZONE 'UTC');")
            server_now = cursor.fetchone()[0]
            time_offset = (datetime.now() - server_now).total_seconds()

            cursor.execute("""
                CREATE OR REPLACE FUNCTION public.now()
                    RETURNS timestamp with time zone AS $$
                        SELECT pg_catalog.now() +  %s * interval '1 second';
                    $$ LANGUAGE sql;
            """, (int(time_offset), ))
            cursor.execute("SELECT (now() AT TIME ZONE 'UTC');")
            new_now = cursor.fetchone()[0]
            _logger.info("Faketime mode, new cursor now is %s", new_now)
            cursor.commit()
    except psycopg2.Error:
        _logger.warning("Unable to set fakedtimed NOW()", exc_info=True)


class DatabaseExists(UserError, ValueError):
    pass


def _create_empty_database(db_name: str) -> None:
    db_system_name = config['db_system']
    try:
        sys_cr = odoo.sql_db.db_connect(db_system_name).cursor()
    except psycopg2.errors.OperationalError:
        # If we use the `db_name` as the system database and we are trying to
        # create it, try to use postgres as the system database.
        if db_system_name == 'postgres' or db_system_name != db_name:
            raise
        _logger.info("Defaulting to 'postgres' system database for database creation")
        sys_cr = odoo.sql_db.db_connect('postgres').cursor()
    with closing(sys_cr) as cr:
        cr.execute("SELECT datname FROM pg_database WHERE datname = %s",
                   (db_name,), log_exceptions=False)
        if cr.fetchall():
            _check_faketime_mode(db_name)
            e = f"Database {db_name!r} already exists!"
            raise DatabaseExists(e)
        # database-altering operations cannot be executed inside a transaction
        cr.rollback()
        cr._cnx.autocommit = True

        # 'C' collate is only safe with template0, but provides more useful indexes
        chosen_template = odoo.tools.config['db_template']
        cr.execute(SQL(
            "CREATE DATABASE %s ENCODING 'unicode' %s TEMPLATE %s",
            quoted_identifier(cr, db_name),
            SQL("LC_COLLATE 'C'") if chosen_template == 'template0' else SQL(""),
            quoted_identifier(cr, chosen_template),
        ))

    # TODO: add --extension=trigram,unaccent
    try:
        db = odoo.sql_db.db_connect(db_name)
        with db.cursor() as cr:
            cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            if odoo.tools.config['unaccent']:
                cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
                # From PostgreSQL's point of view, making 'unaccent' immutable is incorrect
                # because it depends on external data - see
                # https://www.postgresql.org/message-id/flat/201012021544.oB2FiTn1041521@wwwmaster.postgresql.org#201012021544.oB2FiTn1041521@wwwmaster.postgresql.org
                # But in the case of Odoo, we consider that those data don't
                # change in the lifetime of a database. If they do change, all
                # indexes created with this function become corrupted!
                cr.execute("ALTER FUNCTION unaccent(text) IMMUTABLE")
    except psycopg2.Error as e:
        _logger.warning("Unable to create PostgreSQL extensions : %s", e)
    _check_faketime_mode(db_name)

    # restore legacy behaviour on pg15+
    try:
        db = odoo.sql_db.db_connect(db_name)
        with db.cursor() as cr:
            cr.execute("GRANT CREATE ON SCHEMA PUBLIC TO PUBLIC")
    except psycopg2.Error as e:
        _logger.warning("Unable to make public schema public-accessible: %s", e)


def _initialize_db(
    db_name: str,
    *,
    demo: bool,
    user_login: str = 'admin',
    user_password: str,
    lang: str,
    country_code: str | None = None,
    phone: str | None = None,
) -> None:
    """
    Initialize a new registry for ``db_name``, installing the necessary
    base modules and the records for the provided arguments.
    """
    odoo.tools.config['load_language'] = lang

    registry = odoo.modules.registry.Registry.new(db_name, update_module=True, new_db_demo=demo)

    with closing(registry.cursor()) as cr:
        env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})

        if lang:
            modules = env['ir.module.module'].search([('state', '=', 'installed')])
            modules._update_translations(lang)

            main_company_values = {}
            if country_code:
                country = env['res.country'].search([('code', 'ilike', country_code)], limit=1)
                main_company_values = {'country_id': country.id, 'currency_id': country.currency_id.id}
                if len(ct := country_timezones().get(country.code, [])) == 1:
                    env['res.users'].search([]).write({'tz': ct[0]})
            if phone:
                main_company_values['phone'] = phone
            if '@' in user_login:
                main_company_values['email'] = user_login
            if main_company_values:
                env['res.company'].browse(1).write(main_company_values)

        # update admin's password and lang and login
        values = {'password': user_password, 'lang': lang}
        if user_login:
            values['login'] = user_login
            emails = odoo.tools.email_split(user_login)
            if emails:
                values['email'] = emails[0]
        env.ref('base.user_admin').write(values)

        cr.commit()


def create(
    db_name: str,
    *,
    demo: bool,
    user_login: str = 'admin',
    user_password: str,
    lang: str,
    country_code: str | None = None,
    phone: str | None = None,
):
    """
    Create a new database (it must not exists) and install the necessary
    base modules.
    """
    if not DB_NAME_RE.fullmatch(db_name):
        e = f"Invalid {db_name=!r}"
        raise ValueError(e)
    _logger.info("Create database `%s`.", db_name)
    _create_empty_database(db_name)
    return _initialize_db(
        db_name,
        demo=demo,
        user_login=user_login,
        user_password=user_password,
        lang=lang,
        country_code=country_code,
        phone=phone,
    )


def duplicate(
    db_original_name: str,
    db_name: str,
    *,
    neutralize_database: bool = False,
) -> None:
    """
    Create a new database and filestore ``db_name`` (it must not exists)
    using ``db_original_name`` as template. If ``neutralize_database``
    is True then the new database is neutralized.
    """
    if not DB_NAME_RE.fullmatch(db_name):
        e = f"Invalid {db_name=!r}"
        raise ValueError(e)
    _logger.info("Duplicate database `%s` to `%s`.", db_original_name, db_name)
    odoo.sql_db.close_db(db_original_name)
    db = odoo.sql_db.db_connect(config['db_system'])
    with closing(db.cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        _drop_conn(cr, db_original_name)
        cr.execute(SQL(
            "CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s",
            quoted_identifier(cr, db_name),
            quoted_identifier(cr, db_original_name),
        ))

    registry = odoo.modules.registry.Registry.new(db_name)
    with registry.cursor() as cr:
        # force generation of a new dbuuid
        env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})
        env['ir.config_parameter'].init(force=True)
        if neutralize_database:
            odoo.modules.neutralize.neutralize_database(cr)

    from_fs = odoo.tools.config.filestore(db_original_name)
    to_fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(from_fs) and not os.path.exists(to_fs):
        shutil.copytree(from_fs, to_fs)


def _drop_conn(cr: Cursor, db_name: str) -> None:
    """
    Try to terminate all other connections that might prevent dropping
    the database.
    """
    assert cr.dbname == config['db_system']
    assert cr._cnx.autocommit
    with suppress(psycopg2.Error):
        cr.execute("""
            SELECT pg_terminate_backend(pid)
              FROM pg_stat_activity
             WHERE datname = %s
               AND pid != pg_backend_pid()
        """, (db_name,))


def drop(db_name: str) -> None:
    """ Drop the database ``db_name`` and remove its filestore. """
    odoo.modules.registry.Registry.delete(db_name)
    odoo.sql_db.close_db(db_name)

    db = odoo.sql_db.db_connect(config['db_system'])
    with closing(db.cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        _drop_conn(cr, db_name)

        try:
            cr.execute(SQL('DROP DATABASE %s', quoted_identifier(cr, db_name)))
        except psycopg2.Error as e:
            e.add_note(f"When trying to drop {db_name}")
            raise
        _logger.info("DROP DB: %s", db_name)

    fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(fs):
        shutil.rmtree(fs)


def _dump_db_manifest(cr: Cursor):
    pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
    cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
    modules = dict(cr.fetchall())
    return {
        'odoo_dump': '1',
        'db_name': cr.dbname,
        'version': odoo.release.version,
        'version_info': odoo.release.version_info,
        'major_version': odoo.release.major_version,
        'pg_version': pg_version,
        'modules': modules,
    }


def dump(
    db_name: str,
    dump_file,
    *,
    backup_format: typing.Literal['zip', 'dump'] = 'zip',
    with_filestore: bool = True,
):
    """Dump database `db` into file-like object `stream` if stream is None
    return a file object with the dump """
    if backup_format not in ('zip', 'dump'):
        e = f"unknown backup_format: {backup_format!r}"
        raise ValueError(e)
    if not exist(db_name):
        e = f"Database {db_name!r} doesn't exist"
        raise ValueError(e)

    _logger.info("DUMP DB: %s format %s %s filestore", db_name, backup_format, 'with' if with_filestore else 'without')

    cmd = [find_pg_tool('pg_dump'), '--no-owner', db_name]
    env = exec_pg_environ()

    if backup_format == 'zip':
        with tempfile.TemporaryDirectory() as dump_dir:
            if with_filestore:
                filestore = odoo.tools.config.filestore(db_name)
                if os.path.exists(filestore):
                    shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))
            manifest_path = os.path.join(dump_dir, 'manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as manifest_file:
                with odoo.sql_db.db_connect(db_name).cursor() as cr:
                    json.dump(_dump_db_manifest(cr), manifest_file, indent=4)
            cmd.insert(-1, '--file=' + os.path.join(dump_dir, 'dump.sql'))
            subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=True,
            )
            osutil.zip_dir(
                dump_dir,
                dump_file,
                include_dir=False,
                fnct_sort=lambda file_name: file_name != 'dump.sql',
            )
    else:
        cmd.insert(-1, '--format=c')
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
        shutil.copyfileobj(proc.stdout, dump_file)


def restore(
    db_name: str,
    dump_path: os.PathLike,
    *,
    copy: bool = False,
    neutralize_database: bool = False,
) -> None:
    if exist(db_name):
        e = f"Database {db_name!r} already exists"
        raise ValueError(e)

    _logger.info("RESTORING DB: %s", db_name)
    _create_empty_database(db_name)

    filestore_path = None
    with tempfile.TemporaryDirectory() as dump_dir:
        with zipfile.ZipFile(dump_path, 'r') as z:
            # only extract known members!
            filestore = [m for m in z.namelist() if m.startswith('filestore/')]
            z.extractall(dump_dir, ['dump.sql'] + filestore)

            if filestore:
                filestore_path = os.path.join(dump_dir, 'filestore')

        subprocess.run(
            [
                find_pg_tool('psql'),
                '--dbname', db_name,
                '--file', os.path.join(dump_dir, 'dump.sql'),
                '--quiet',
            ],
            env=exec_pg_environ(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )

        registry = odoo.modules.registry.Registry.new(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                env['ir.config_parameter'].init(force=True)
            if neutralize_database:
                odoo.modules.neutralize.neutralize_database(cr)

            if filestore_path:
                filestore_dest = env['ir.attachment']._filestore()
                shutil.move(filestore_path, filestore_dest)

    _logger.info("RESTORE DB: %s", db_name)


def rename(
    old_name: str,
    new_name: str,
) -> None:
    odoo.modules.registry.Registry.delete(old_name)
    odoo.sql_db.close_db(old_name)

    db = odoo.sql_db.db_connect(config['db_system'])
    with closing(db.cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        _drop_conn(cr, old_name)
        try:
            cr.execute(SQL(
                'ALTER DATABASE %s RENAME TO %s',
                quoted_identifier(cr, old_name),
                quoted_identifier(cr, new_name),
            ))
        except psycopg2.Error as e:
            e.add_note(f"Renaming {old_name} to {new_name}")
            raise
        _logger.info("RENAME DB: %s -> %s", old_name, new_name)

    old_fs = odoo.tools.config.filestore(old_name)
    new_fs = odoo.tools.config.filestore(new_name)
    if os.path.exists(old_fs) and not os.path.exists(new_fs):
        shutil.move(old_fs, new_fs)


def list_dbs(*, force=False):
    if not force:
        verify_db_management_enabled()

    if not odoo.tools.config['dbfilter'] and odoo.tools.config['db_name']:
        # In case --db-filter is not provided and --database is passed, Odoo will not
        # fetch the list of databases available on the postgres server and instead will
        # use the value of --database as comma seperated list of exposed databases.
        return sorted(odoo.tools.config['db_name'])

    chosen_template = odoo.tools.config['db_template']
    ignore_templates_list = tuple({'postgres', chosen_template})
    db = odoo.sql_db.db_connect(config['db_system'])
    with closing(db.cursor()) as cr:
        try:
            cr.execute("""
                SELECT datname
                  FROM pg_database
                 WHERE datdba = (
                      SELECT usesysid
                        FROM pg_user
                       WHERE usename = current_user
                   )
                   AND NOT datistemplate
                   AND datallowconn
                   AND datname NOT IN %s
              ORDER BY datname
            """, (ignore_templates_list,))
            return [name for (name,) in cr.fetchall()]
        except psycopg2.Error:
            _logger.exception("Listing databases failed:")
            return []


def exist(db_name):
    try:
        odoo.sql_db.db_connect(db_name).cursor().close()
    except psycopg2.OperationalError:
        return False
    else:
        return True
