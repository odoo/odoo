from odoo.db import schema
from odoo.tools import SQL

MODULES = {"api_ai": "gateway_ml"}

MODELS = {
    "ai.provider": "gateway.ml.provider",
    "ai.model": "gateway.ml.model",
    "ai.model.fallback": "gateway.ml.model.fallback",
}

OLD_MODELS = list(MODELS)
NEW_MODELS = [MODELS[m] for m in OLD_MODELS]

TABLES = dict(
    sorted(
        ((o.replace(".", "_"), n.replace(".", "_")) for o, n in MODELS.items()),
        key=lambda kv: -len(kv[0]),
    )
)

GENERATED_XMLID_PREFIXES = ("field_{}__", "selection__{}__", "model_inherit__{}__")

MODEL_COLUMNS = (
    "model",
    "model_id",
    "res_model",
    "model_name",
    "src_model",
    "parent_res_model",
    "relation",
    "res_model_name",
    "alias_model",
    "gate_model",
)

EXPRESSION_COLUMNS = (
    ("ir_act_window", ("domain", "context")),
    ("ir_act_server", ("code",)),
    ("ir_filters", ("domain", "context", "sort")),
    ("ir_ui_view", ("arch_db",)),
    ("ir_embedded_actions", ("domain", "context")),
)


def _rename_table(cr, old, new):
    if not schema.table_exists(cr, old) or schema.table_exists(cr, new):
        return
    cr.execute(
        SQL("ALTER TABLE %s RENAME TO %s", SQL.identifier(old), SQL.identifier(new))
    )
    cr.execute(
        "SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass AND conname LIKE %s",
        [new, old + "\\_%"],
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER TABLE %s RENAME CONSTRAINT %s TO %s",
                SQL.identifier(new),
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        """
        SELECT indexname FROM pg_indexes
         WHERE schemaname = current_schema() AND tablename = %s AND indexname LIKE %s
        """,
        [new, old + "\\_%"],
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER INDEX %s RENAME TO %s",
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        """
        SELECT 1 FROM pg_sequences
         WHERE schemaname = current_schema() AND sequencename = %s
        """,
        [old + "_id_seq"],
    )
    if cr.fetchone():
        cr.execute(
            SQL(
                "ALTER SEQUENCE %s RENAME TO %s",
                SQL.identifier(old + "_id_seq"),
                SQL.identifier(new + "_id_seq"),
            )
        )


def _rename_model_tables(cr):
    for old, new in TABLES.items():
        _rename_table(cr, old, new)


def _repoint_model_names(cr):
    cr.execute(
        """
        SELECT c.table_name, c.column_name
          FROM information_schema.columns c
          JOIN information_schema.tables t
            ON t.table_schema = c.table_schema AND t.table_name = c.table_name
         WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE'
           AND c.data_type IN ('character varying', 'text')
           AND c.column_name = ANY(%s)
        """,
        [list(MODEL_COLUMNS)],
    )
    for table, column in cr.fetchall():
        cr.execute(
            SQL(
                """
                UPDATE %s AS target SET %s = renames.new
                  FROM (SELECT unnest(%s::text[]) AS old, unnest(%s::text[]) AS new)
                       AS renames
                 WHERE target.%s = renames.old
                """,
                SQL.identifier(table),
                SQL.identifier(column),
                OLD_MODELS,
                NEW_MODELS,
                SQL.identifier(column),
            )
        )


def _rewrite_reference_values(cr):
    cr.execute(
        """
        SELECT f.model, f.name
          FROM ir_model_fields f
         WHERE f.ttype = 'reference' AND f.store
        """
    )
    for model, field in cr.fetchall():
        table = model.replace(".", "_")
        if not schema.column_exists(cr, table, field):
            continue
        for old, new in MODELS.items():
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = %s || substring(%s from %s) WHERE %s LIKE %s",
                    SQL.identifier(table),
                    SQL.identifier(field),
                    new + ",",
                    SQL.identifier(field),
                    len(old) + 2,
                    SQL.identifier(field),
                    old.replace("_", "\\_") + ",%",
                )
            )


def _rewrite_expressions(cr):
    for table, columns in EXPRESSION_COLUMNS:
        if not schema.table_exists(cr, table):
            continue
        for column in columns:
            if not schema.column_exists(cr, table, column):
                continue
            for old, new in MODELS.items():
                for quote in ("'", '"'):
                    needle, replacement = f"{quote}{old}{quote}", f"{quote}{new}{quote}"
                    rewritten = SQL(
                        "replace(%s::text, %s, %s)",
                        SQL.identifier(column),
                        needle,
                        replacement,
                    )
                    cr.execute(
                        SQL(
                            "UPDATE %s SET %s = %s WHERE position(%s in %s::text) > 0",
                            SQL.identifier(table),
                            SQL.identifier(column),
                            SQL("%s::jsonb", rewritten)
                            if column == "arch_db"
                            else rewritten,
                            needle,
                            SQL.identifier(column),
                        )
                    )


def _rename_modules(cr):
    for old, new in MODULES.items():
        cr.execute(
            """
            DELETE FROM ir_model_data dissolved USING ir_model_data surviving
                  WHERE dissolved.module = %s AND surviving.module = %s
                    AND surviving.name = dissolved.name
            """,
            [old, new],
        )
        cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", [new, old])
        cr.execute(
            "DELETE FROM ir_module_module WHERE name = %s AND state = 'uninstalled'"
            " AND EXISTS (SELECT 1 FROM ir_module_module WHERE name = %s)"
            " RETURNING id",
            [new, old],
        )
        if dissolved_ids := [row[0] for row in cr.fetchall()]:
            cr.execute(
                "DELETE FROM ir_model_data WHERE model = 'ir.module.module'"
                " AND res_id = ANY(%s)",
                [dissolved_ids],
            )
        cr.execute("UPDATE ir_module_module SET name = %s WHERE name = %s", [new, old])
        for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
            if schema.table_exists(cr, table):
                cr.execute(
                    SQL(
                        "UPDATE %s SET name = %s WHERE name = %s",
                        SQL.identifier(table),
                        new,
                        old,
                    )
                )
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s
             WHERE module = 'base' AND model = 'ir.module.module' AND name = %s
            """,
            [f"module_{new}", f"module_{old}"],
        )
    cr.execute(
        "UPDATE ir_module_module SET data_file_checksums = NULL WHERE name = ANY(%s)",
        [list(MODULES.values())],
    )


def _rename_xml_ids(cr):
    for old, new in TABLES.items():
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s
             WHERE model = 'ir.model' AND name = %s
            """,
            [f"model_{new}", f"model_{old}"],
        )
        for pattern in GENERATED_XMLID_PREFIXES:
            old_prefix, new_prefix = pattern.format(old), pattern.format(new)
            cr.execute(
                """
                UPDATE ir_model_data SET name = %s || substring(name from %s)
                 WHERE name LIKE %s
                """,
                [new_prefix, len(old_prefix) + 1, old_prefix.replace("_", "\\_") + "%"],
            )
    if schema.table_exists(cr, "ir_model_constraint"):
        for old, new in TABLES.items():
            cr.execute(
                """
                UPDATE ir_model_constraint SET name = %s || substring(name from %s)
                 WHERE name LIKE %s
                   AND model IN (SELECT id FROM ir_model WHERE model = %s)
                """,
                [
                    new,
                    len(old) + 1,
                    old.replace("_", "\\_") + "\\_%",
                    MODELS_BY_TABLE[new],
                ],
            )


def _rename_config_parameters(cr):
    cut = len("api_ai.") + 1
    cr.execute(
        r"""
        UPDATE ir_config_parameter
           SET key = 'gateway_ml.' || substring(key from %s)
         WHERE key LIKE 'api\_ai.%%'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter existing
                WHERE existing.key =
                      'gateway_ml.' || substring(ir_config_parameter.key from %s)
           )
        """,
        [cut, cut],
    )


MODELS_BY_TABLE = {new.replace(".", "_"): new for new in NEW_MODELS}


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = 'api_ai'")
    if not cr.fetchone():
        return
    _rename_model_tables(cr)
    _repoint_model_names(cr)
    _rewrite_reference_values(cr)
    _rewrite_expressions(cr)
    _rename_modules(cr)
    _rename_xml_ids(cr)
    _rename_config_parameters(cr)
