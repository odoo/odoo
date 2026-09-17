import logging
import typing
from contextlib import closing
from itertools import batched

from psycopg.types.json import Json

import odoo.api
import odoo.tools
from odoo.db import schema as _db_schema
from odoo.libs.debug_log import DebugLog
from odoo.modules._protocols import SqlReader
from odoo.modules.module import Manifest

from .registry import Registry

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from odoo.db import Cursor

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_AUTO_INSTALL_CANDIDATES_QUERY = """
    SELECT m.name FROM ir_module_module m
    WHERE m.auto_install
    AND state not in ('to install', 'uninstallable')
    AND NOT EXISTS (
        SELECT 1 FROM ir_module_module_dependency d
        LEFT JOIN ir_module_module mdep ON (d.name = mdep.name)
        WHERE d.module_id = m.id
          AND (
              mdep.id IS NULL
              -- an uninstallable dependency (required or not) can never be
              -- satisfied, so the module cannot be installed at all
              OR mdep.state = 'uninstallable'
              OR (d.auto_install_required AND mdep.state != 'to install')
          )
    )"""

_AUTO_INSTALL_CLOSURE_QUERY = """
    SELECT d.name FROM ir_module_module_dependency d
    JOIN ir_module_module m ON (d.module_id = m.id)
    JOIN ir_module_module mdep ON (d.name = mdep.name)
    WHERE (m.state = 'to install' OR m.name = any(%s))
        -- don't re-mark marked modules
    AND NOT (mdep.state = 'to install' OR mdep.name = any(%s))
        -- never mark an uninstallable module: it cannot be installed, and
        -- overwriting its state would corrupt it (the dependent module is
        -- reported and skipped by the module graph at load time instead)
    AND mdep.state != 'uninstallable'
    """


def is_initialized(cr: Cursor) -> bool:
    return _db_schema.table_exists(cr, "ir_module_module")


_MODULE_COLUMNS = (
    "author",
    "website",
    "name",
    "shortdesc",
    "description",
    "category_id",
    "auto_install",
    "state",
    "web",
    "license",
    "application",
    "icon",
    "sequence",
    "summary",
)

_MODULE_INSERT_CHUNK = 1000


def _insert_modules(cr: SqlReader, rows: list[tuple]) -> dict[str, int]:
    placeholder = "(" + ", ".join(["%s"] * len(_MODULE_COLUMNS)) + ")"
    columns = ", ".join(_MODULE_COLUMNS)
    ids: dict[str, int] = {}
    with _debug.perf("modules.db.insert_modules", cr=cr, rows=len(rows)) as span:
        chunks = 0  # debuglog
        for chunk in batched(rows, _MODULE_INSERT_CHUNK, strict=False):
            chunks += 1  # debuglog
            cr.execute(
                f"INSERT INTO ir_module_module ({columns}) VALUES "
                + ", ".join([placeholder] * len(chunk))
                + " RETURNING id, name",
                [value for row in chunk for value in row],
            )
            ids.update({name: module_id for module_id, name in cr.fetchall()})
        span.set(chunks=chunks, inserted=len(ids))
    return ids


def _create_base_schema(cr: Cursor) -> None:
    try:
        f = odoo.tools.misc.file_path("base/data/base_data.sql")
    except FileNotFoundError as e:
        m = "File not found: 'base/data/base_data.sql' (provided by module 'base')."
        _logger.critical(m)
        raise OSError(m) from e

    with (
        odoo.tools.misc.file_open(f) as base_sql_file,
        _debug.perf("modules.db.base_schema", cr=cr, path=f),
    ):
        cr.execute(base_sql_file.read())


def _copy_module_metadata(
    cr: Cursor, manifests: Iterable[Manifest], module_ids: dict[str, int]
) -> None:
    all_data_rows: list[tuple[str, str, str, int, bool]] = []
    all_dep_rows: list[tuple[int, str, bool]] = []
    for info in manifests:
        module_id = module_ids[info.name]
        all_data_rows.append(
            (
                "module_" + info.name,
                "ir.module.module",
                "base",
                module_id,
                True,
            ),
        )
        triggers = info["auto_install"] or ()
        all_dep_rows.extend((module_id, d, d in triggers) for d in info["depends"])

    with _debug.perf(
        "modules.db.copy_module_metadata",
        cr=cr,
        xmlids=len(all_data_rows),
        dependencies=len(all_dep_rows),
    ):
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


def _mark_auto_install_modules(cr: Cursor) -> None:
    iteration = 0  # debuglog
    marked = 0  # debuglog
    with _debug.perf("modules.db.mark_auto_install", cr=cr) as span:
        while True:
            iteration += 1  # debuglog
            cr.execute(_AUTO_INSTALL_CANDIDATES_QUERY)
            to_auto_install = [x[0] for x in cr.fetchall()]
            candidates = len(to_auto_install)  # debuglog
            cr.execute(_AUTO_INSTALL_CLOSURE_QUERY, [to_auto_install, to_auto_install])
            to_auto_install.extend(x[0] for x in cr.fetchall())
            _debug.logic(
                "modules.db.auto_install.iteration",
                iteration=iteration,
                candidates=candidates,
                closure=len(to_auto_install) - candidates,
            )

            if not to_auto_install:
                break
            marked += len(to_auto_install)  # debuglog
            cr.execute(
                """UPDATE ir_module_module SET state='to install' WHERE name = ANY(%s)""",
                (list(to_auto_install),),
            )
        span.set(iterations=iteration, marked=marked)


def initialize(cr: Cursor) -> None:
    _debug.pipeline("modules.db.initialize", db=cr.dbname)
    _create_base_schema(cr)

    manifests = Manifest.get_all_addon_manifests()
    category_cache: dict[str, int] = {}
    module_rows = [
        (
            info["author"],
            info["website"],
            info.name,
            Json({"en_US": info["name"]}),
            Json({"en_US": info["description"]}),
            get_or_create_category_id(cr, info["category"].split("/"), category_cache),
            info["auto_install"] is not False,
            "uninstalled" if info["installable"] else "uninstallable",
            info["web"],
            info["license"],
            info["application"],
            info["icon"],
            info["sequence"],
            Json({"en_US": info["summary"]}),
        )
        for info in manifests
    ]
    module_ids = _insert_modules(cr, module_rows)
    _copy_module_metadata(cr, manifests, module_ids)
    _debug.lifecycle(
        "modules.db.initialized",
        db=cr.dbname,
        manifests=len(manifests),
        modules=len(module_ids),
        categories=len(category_cache),
        skip_auto_install=bool(odoo.tools.config.get("skip_auto_install")),
    )

    if odoo.tools.config.get("skip_auto_install"):
        _debug.logic("modules.db.auto_install.skipped", db=cr.dbname)
        cr.execute(
            """UPDATE ir_module_module SET state='to install' WHERE name = 'base'"""
        )
        return

    _mark_auto_install_modules(cr)


def category_xml_id(categories: list[str]) -> str:
    slug = "_".join(x.lower() for x in categories).replace("&", "and").replace(" ", "_")
    return f"module_category_{slug}"


def get_or_create_category_id(
    cr: Cursor,
    categories: list[str],
    category_cache: dict[str, int] | None = None,
) -> int | None:
    p_id = None
    built = []
    for cat_name in categories:
        built.append(cat_name)
        xml_id = category_xml_id(built)
        if category_cache is not None and xml_id in category_cache:
            p_id = category_cache[xml_id]
            continue
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE name=%s AND module=%s AND model=%s",
            (xml_id, "base", "ir.module.category"),
        )

        row = cr.fetchone()
        if not row:
            cr.execute(
                """
                INSERT INTO ir_module_category (name, parent_id)
                VALUES (%s, %s) RETURNING id
            """,
                (Json({"en_US": cat_name}), p_id),
            )
            row = cr.fetchone()
            if row is None:
                raise RuntimeError(f"INSERT of category {cat_name!r} returned no id")
            p_id = row[0]
            cr.execute(
                """
                INSERT INTO ir_model_data (module, name, res_id, model, noupdate)
                VALUES (%s, %s, %s, %s, %s)
            """,
                ("base", xml_id, p_id, "ir.module.category", True),
            )
            _debug.lifecycle(
                "modules.db.category_created",
                xml_id=xml_id,
                id=p_id,
                depth=len(built),
            )
        else:
            p_id = row[0]
        if not isinstance(p_id, int):
            raise RuntimeError(
                f"category {xml_id!r} resolved to non-integer id {p_id!r}"
                " (NULL res_id in ir_model_data?)"
            )
        if category_cache is not None:
            category_cache[xml_id] = p_id
    return p_id


def initialize_db(
    db_name: str,
    demo: bool,
    lang: str | None,
    user_password: str,
    login: str = "admin",
    country_code: str | None = None,
    phone: str | None = None,
) -> None:
    normalized_country = country_code.upper() if country_code else None

    saved_load_language = odoo.tools.config.get("load_language")
    try:
        odoo.tools.config["load_language"] = lang

        _debug.pipeline(
            "modules.db.initialize_db.begin",
            db=db_name,
            demo=demo,
            lang=lang,
            country=normalized_country,
        )
        with _debug.perf("modules.db.initialize_db.registry", db=db_name):
            registry = Registry.new(
                db_name, update_module=True, new_db_demo=demo, run_tests=False
            )

        with closing(registry.cursor()) as cr:
            env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})

            if lang:
                modules = env["ir.module.module"].search([("state", "=", "installed")])
                with _debug.perf(
                    "modules.db.initialize_db.translations",
                    cr=cr,
                    lang=lang,
                    modules=len(modules),
                ):
                    modules._update_translations(lang)

            if normalized_country:
                country = env["res.country"].search(
                    [("code", "ilike", normalized_country)], limit=1
                )
                _debug.logic(
                    "modules.db.initialize_db.country",
                    code=normalized_country,
                    found=bool(country),
                    currency=bool(country and country.currency_id),
                )
                if country:
                    company_values = {"country_id": country.id}
                    if country.currency_id:
                        company_values["currency_id"] = country.currency_id.id
                    env["res.company"].browse(1).write(company_values)
                    from odoo.libs.datetime import country_timezones

                    tz_mapping = country_timezones()
                    timezones = tz_mapping.get(normalized_country) or ()
                    _debug.logic(
                        "modules.db.initialize_db.timezone",
                        code=normalized_country,
                        candidates=len(timezones),
                        applied=len(timezones) == 1,
                    )
                    if len(timezones) == 1:
                        users = env["res.users"].search([])
                        users.write({"tz": timezones[0]})

            if phone:
                env["res.company"].browse(1).write(
                    {"phone_ids": [(0, 0, {"number": phone})]}
                )

            if login and "@" in login:
                env["res.company"].browse(1).write({"email": login})

            values = {"password": user_password, "lang": lang}
            if login:
                values["login"] = login
                emails = odoo.tools.email_split(login)
                if emails:
                    values["email"] = emails[0]
            env.ref("base.user_admin").write(values)

            cr.commit()
            _debug.lifecycle(
                "modules.db.initialize_db",
                db=db_name,
                demo=demo,
                lang=lang,
                country=normalized_country,
                login=login,
            )
    except Exception:
        _logger.exception("CREATE DATABASE failed:")
        raise
    finally:
        if saved_load_language is None:
            odoo.tools.config.pop("load_language", None)
        else:
            odoo.tools.config["load_language"] = saved_load_language
