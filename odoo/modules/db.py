import logging
import typing
from contextlib import closing
from enum import IntEnum

from psycopg.types.json import Json

import odoo.api
import odoo.modules
import odoo.modules.registry
import odoo.tools

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor, Cursor

_logger = logging.getLogger(__name__)


def is_initialized(cr: Cursor) -> bool:
    """Check if a database has been initialized for the ORM.

    The database can be initialized with the 'initialize' function below.

    """
    return odoo.tools.sql.table_exists(cr, "ir_module_module")


def initialize(cr: Cursor) -> None:
    """Initialize a database for the ORM.

    This executes base/data/base_data.sql, creates the ir_module_categories
    (taken from each module descriptor file), and creates the ir_module_module
    and ir_model_data entries.

    """
    try:
        f = odoo.tools.misc.file_path("base/data/base_data.sql")
    except FileNotFoundError:
        m = "File not found: 'base/data/base_data.sql' (provided by module 'base')."
        _logger.critical(m)
        raise OSError(m)

    with odoo.tools.misc.file_open(f) as base_sql_file:
        cr.execute(base_sql_file.read())  # pylint: disable=sql-injection

    # Collect batched rows for COPY at end (avoids 500-2000 individual INSERTs)
    all_data_rows = []  # ir_model_data rows
    all_dep_rows = []  # ir_module_module_dependency rows

    for info in odoo.modules.Manifest.all_addon_manifests():
        module_name = info.name
        categories = info["category"].split("/")
        category_id = create_categories(cr, categories)

        if info["installable"]:
            state = "uninstalled"
        else:
            state = "uninstallable"

        cr.execute("""
            INSERT INTO ir_module_module
                (author, website, name, shortdesc, description,
                 category_id, auto_install, state, web, license, application, icon, sequence, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                info["author"],
                info["website"],
                module_name,
                Json({"en_US": info["name"]}),
                Json({"en_US": info["description"]}),
                category_id,
                info["auto_install"] is not False,
                state,
                info["web"],
                info["license"],
                info["application"],
                info["icon"],
                info["sequence"],
                Json({"en_US": info["summary"]}),
            ),
        )
        row = cr.fetchone()
        assert row is not None  # for typing
        module_id = row[0]

        all_data_rows.append(
            (
                "module_" + module_name,
                "ir.module.module",
                "base",
                module_id,
                True,
            ),
        )
        dependencies = info["depends"]
        all_dep_rows.extend((module_id, d, d in (info["auto_install"] or ())) for d in dependencies)

    # Batch insert all ir_model_data and dependency rows via COPY
    if all_data_rows:
        cr.copy_from(
            "ir_model_data",
            ["name", "model", "module", "res_id", "noupdate"],
            all_data_rows,
        )
    if all_dep_rows:
        cr.copy_from(
            "ir_module_module_dependency",
            ["module_id", "name", "auto_install_required"],
            all_dep_rows,
        )

    if odoo.tools.config.get("skip_auto_install"):
        # even if skip_auto_install is enabled we still want to have base
        cr.execute(
            """UPDATE ir_module_module SET state='to install' WHERE name = 'base'"""
        )
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
        cr.execute(
            """
        SELECT d.name FROM ir_module_module_dependency d
        JOIN ir_module_module m ON (d.module_id = m.id)
        JOIN ir_module_module mdep ON (d.name = mdep.name)
        WHERE (m.state = 'to install' OR m.name = any(%s))
            -- don't re-mark marked modules
        AND NOT (mdep.state = 'to install' OR mdep.name = any(%s))
        """,
            [to_auto_install, to_auto_install],
        )
        to_auto_install.extend(x[0] for x in cr.fetchall())

        if not to_auto_install:
            break
        cr.execute(
            """UPDATE ir_module_module SET state='to install' WHERE name = ANY(%s)""",
            (list(to_auto_install),),
        )


def create_categories(cr: Cursor, categories: list[str]) -> int | None:
    """Create the ir_module_category entries for some categories.

    categories is a list of strings forming a single category with its
    parent categories, like ['Grand Parent', 'Parent', 'Child'].

    Return the database id of the (last) category.

    """
    p_id = None
    built = []
    for cat_name in categories:
        built.append(cat_name)
        xml_id = "module_category_" + ("_".join(x.lower() for x in built)).replace(
            "&", "and"
        ).replace(" ", "_")
        # search via xml_id (because some categories are renamed)
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE name=%s AND module=%s AND model=%s",
            (xml_id, "base", "ir.module.category"),
        )

        row = cr.fetchone()
        if not row:
            cr.execute("""
                INSERT INTO ir_module_category (name, parent_id)
                VALUES (%s, %s) RETURNING id
            """, (Json({"en_US": cat_name}), p_id))
            row = cr.fetchone()
            assert row is not None  # for typing
            p_id = row[0]
            cr.execute("""
                INSERT INTO ir_model_data (module, name, res_id, model, noupdate)
                VALUES (%s, %s, %s, %s, %s)
            """, ("base", xml_id, p_id, "ir.module.category", True))
        else:
            p_id = row[0]
        assert isinstance(p_id, int)
    return p_id


class FunctionStatus(IntEnum):
    MISSING = 0  # function is not present (falsy)
    PRESENT = 1  # function is present but not indexable (not immutable)
    INDEXABLE = 2  # function is present and indexable (immutable)


def has_unaccent(cr: BaseCursor) -> FunctionStatus:
    """Test whether the database has function 'unaccent' and return its status.

    The unaccent is supposed to be provided by the PostgreSQL unaccent contrib
    module but any similar function will be picked by Odoo.

    :rtype: FunctionStatus
    """
    cr.execute("""
        SELECT p.provolatile
        FROM pg_proc p
        WHERE p.proname = 'unaccent'
              AND p.pronamespace = current_schema::regnamespace
              AND p.pronargs = 1
    """)
    result = cr.fetchone()
    if not result:
        return FunctionStatus.MISSING
    # The `provolatile` of unaccent allows to know whether the unaccent function
    # can be used to create index (it should be 'i' - means immutable), see
    # https://www.postgresql.org/docs/current/catalog-pg-proc.html.
    return FunctionStatus.INDEXABLE if result[0] == "i" else FunctionStatus.PRESENT


def has_trigram(cr: BaseCursor) -> bool:
    """Test if the database has the a word_similarity function.

    The word_similarity is supposed to be provided by the PostgreSQL built-in
    pg_trgm module but any similar function will be picked by Odoo.

    """
    cr.execute("SELECT proname FROM pg_proc WHERE proname='word_similarity'")
    return bool(cr.fetchone())


def initialize_db(
    db_name: str,
    demo: bool,
    lang: str | None,
    user_password: str,
    login: str = "admin",
    country_code: str | None = None,
    phone: str | None = None,
) -> None:
    """Initialize a new database with modules, admin user, and company settings.

    This function handles the high-level initialization of a new Odoo database,
    including:
    - Creating the module registry and loading modules
    - Installing language translations
    - Configuring the company based on country
    - Setting up the admin user credentials

    This complements the low-level `initialize()` function which handles
    schema creation.

    :param db_name: Name of the database to initialize
    :param demo: Whether to install demo data
    :param lang: Language code (e.g., 'en_US', 'fr_FR')
    :param user_password: Password for the admin user
    :param login: Login name for the admin user (default: 'admin')
    :param country_code: ISO country code for company configuration
    :param phone: Phone number for the company
    """
    try:
        odoo.tools.config["load_language"] = lang

        registry = odoo.modules.registry.Registry.new(
            db_name, update_module=True, new_db_demo=demo
        )

        with closing(registry.cursor()) as cr:
            env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})

            if lang:
                modules = env["ir.module.module"].search([("state", "=", "installed")])
                modules._update_translations(lang)

            if country_code:
                country = env["res.country"].search(
                    [("code", "ilike", country_code)], limit=1
                )
                if country:
                    env["res.company"].browse(1).write(
                        {
                            "country_id": country.id,
                            "currency_id": country.currency_id.id,
                        }
                    )
                    from odoo.libs.datetime.tz import country_timezones

                    tz_mapping = country_timezones()
                    if len(tz_mapping.get(country_code, [])) == 1:
                        users = env["res.users"].search([])
                        users.write({"tz": tz_mapping[country_code][0]})

            if phone:
                env["res.company"].browse(1).write({"phone": phone})

            if login and "@" in login:
                env["res.company"].browse(1).write({"email": login})

            # Update admin's password and lang and login
            values = {"password": user_password, "lang": lang}
            if login:
                values["login"] = login
                emails = odoo.tools.email_split(login)
                if emails:
                    values["email"] = emails[0]
            env.ref("base.user_admin").write(values)

            cr.commit()
    except Exception:
        _logger.exception("CREATE DATABASE failed:")
        raise
