"""`ir_model_access`, `ir_rule` and `rule_group_rel` go with their models.

1.97 converted every access line and record rule into ir.access rows and
emptied the three tables; the two models are gone from the code. This runs at
the end stage, not before the modules load: no migration of the four repositories
reaches the tables any more (test_lint's test_access_migrations holds them to
that), but one shipped elsewhere may, and after 1.97 it touches empty tables
where dropping them first would make it fail.

A row that is back in a table by now was written after 1.97 converted, so it is
converted the same way before the drop, never lost. The metadata goes with the
tables, so `_process_end` has nothing to unlink: the `ir_model` rows of the two
models (their fields, constraints and relations cascade) and every external id
naming them, their fields or an ir.access row on them.
"""

import logging

from odoo.modules.module import get_module_path, load_script

from odoo.addons.base.models.ir_access_convert import (
    noupdate_shortfalls,
    read_shipped_access_rows,
)

_logger = logging.getLogger(__name__)

TABLES = ("rule_group_rel", "ir_rule", "ir_model_access")
MODELS = ("ir.model.access", "ir.rule")


def _existing(cr) -> list[str]:
    cr.execute(
        "SELECT relname FROM pg_class WHERE relkind = 'r' AND relname = ANY(%s)",
        [list(TABLES)],
    )
    return [name for [name] in cr.fetchall()]


def migrate(cr, version):
    if not version:
        return
    tables = _existing(cr)
    if {"ir_rule", "ir_model_access"} <= set(tables):
        cr.execute(
            "SELECT (SELECT count(*) FROM ir_model_access),"
            " (SELECT count(*) FROM ir_rule)"
        )
        lines, rules = cr.fetchone()
        if lines or rules:
            _logger.warning(
                "%s access lines and %s record rules were written after 1.97 "
                "converted the tables; converting them before the drop",
                lines,
                rules,
            )
            load_script(
                f"{get_module_path('base')}/migrations/1.97/"
                "pre-migrate_ir_access_rows.py",
                "base_1_100_convert_late_access_rows",
            ).migrate(cr, version)
    for table in tables:
        cr.execute(f'DROP TABLE "{table}" CASCADE')
    cr.execute("SELECT id FROM ir_model WHERE model = ANY(%s)", [list(MODELS)])
    model_ids = [model_id for [model_id] in cr.fetchall()]
    if model_ids:
        cr.execute(
            """
            DELETE FROM ir_model_data d USING ir_access a
             WHERE d.model = 'ir.access' AND d.res_id = a.id
               AND a.model_id = ANY(%s)
            """,
            [model_ids],
        )
        cr.execute(
            """
            DELETE FROM ir_model_data d
             USING ir_model_fields_selection s
              JOIN ir_model_fields f ON f.id = s.field_id
             WHERE d.model = 'ir.model.fields.selection' AND d.res_id = s.id
               AND f.model_id = ANY(%s)
            """,
            [model_ids],
        )
        cr.execute(
            """
            DELETE FROM ir_model_data d USING ir_model_fields f
             WHERE d.model = 'ir.model.fields' AND d.res_id = f.id
               AND f.model_id = ANY(%s)
            """,
            [model_ids],
        )
        cr.execute(
            """
            DELETE FROM ir_model_data d USING ir_model_constraint c
             WHERE d.model = 'ir.model.constraint' AND d.res_id = c.id
               AND c.model = ANY(%s)
            """,
            [model_ids],
        )
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id = ANY(%s)",
            [model_ids],
        )
        cr.execute("DELETE FROM ir_model WHERE id = ANY(%s)", [model_ids])
    cr.execute("DELETE FROM ir_model_data WHERE model = ANY(%s)", [list(MODELS)])
    _logger.info(
        "dropped %s and the metadata of %s", ", ".join(tables), ", ".join(MODELS)
    )
    # 1.97 named the noupdate rows its conversion left short of their file; by
    # now every module's migration has run, so a row named here was handed over
    # by none of them
    cr.execute(
        "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade')"
    )
    modules = [name for [name] in cr.fetchall()]
    shipped = read_shipped_access_rows(modules)
    shortfalls = noupdate_shortfalls(cr, shipped, modules)
    for xmlid, model, missing in shortfalls:
        _logger.warning(
            "noupdate row %s on %s still lacks %s, which its module's file grants "
            "and no other row does",
            xmlid,
            model,
            missing,
        )
    _logger.info("%s noupdate access row(s) short of their file", len(shortfalls))
