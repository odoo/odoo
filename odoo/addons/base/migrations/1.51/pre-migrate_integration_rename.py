from odoo.db import schema
from odoo.tools import SQL

MODULES = {"api_transport": "integration"}

MODELS = {
    "api.endpoint.outbound": "integration.service",
    "api.endpoint.inbound": "mixin.integration.receiver",
    "api.event.log": "integration.exchange",
    "api.response.cache": "integration.response.cache",
    "mixin.api.channel": "mixin.integration.channel",
}

OLD_MODELS = list(MODELS)
NEW_MODELS = [MODELS[m] for m in OLD_MODELS]

TABLES = dict(
    sorted(
        ((o.replace(".", "_"), n.replace(".", "_")) for o, n in MODELS.items()),
        key=lambda kv: -len(kv[0]),
    )
)

NAME_TOKENS = (*TABLES.items(), ("api_transport", "integration"))

PROTECTED_NAMES = (
    "group\\_api\\_transport\\_%",
    "res\\_groups\\_privilege\\_api\\_transport",
    "module\\_category\\_api\\_transport",
)

JOB_CHANNELS = {"api_transport_inbound": "integration_inbound"}

XML_IDS = {
    ("api_transport", "menu_api_endpoint_outbounds"): "menu_integration_service_list"
}

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


def _new_table(name):
    for old, new in TABLES.items():
        if name == old:
            return new
        if name.startswith(old + "_"):
            return new + name[len(old) :]
        if name.endswith("_" + old + "_rel"):
            return name[: -len(old) - 4] + new + "_rel"
        if name.endswith("_" + old):
            return name[: -len(old)] + new
    return None


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


def _rename_many2many(cr):
    cr.execute(
        """
        SELECT DISTINCT relation_table, column1, column2 FROM ir_model_fields
         WHERE ttype = 'many2many' AND relation_table IS NOT NULL
        """
    )
    for table, col1, col2 in cr.fetchall():
        new_table = _new_table(table) or table
        cols = {}
        for col in (col1, col2):
            if col and col.endswith("_id"):
                new = _new_table(col[:-3])
                if new:
                    cols[col] = new + "_id"
        if new_table == table and not cols:
            continue
        if schema.table_exists(cr, table):
            for col, new_col in cols.items():
                if schema.column_exists(cr, table, col) and not schema.column_exists(
                    cr, table, new_col
                ):
                    cr.execute(
                        SQL(
                            "ALTER TABLE %s RENAME COLUMN %s TO %s",
                            SQL.identifier(table),
                            SQL.identifier(col),
                            SQL.identifier(new_col),
                        )
                    )
            _rename_table(cr, table, new_table)
        cr.execute(
            """
            UPDATE ir_model_fields SET relation_table = %s, column1 = %s, column2 = %s
             WHERE ttype = 'many2many' AND relation_table = %s
            """,
            [new_table, cols.get(col1, col1), cols.get(col2, col2), table],
        )
        if schema.table_exists(cr, "ir_model_relation"):
            cr.execute(
                "UPDATE ir_model_relation SET name = %s WHERE name = %s",
                [new_table, table],
            )


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
            " AND EXISTS (SELECT 1 FROM ir_module_module WHERE name = %s)",
            [new, old],
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
    for (module, old), new in XML_IDS.items():
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s
             WHERE module = %s AND name = %s
            """,
            [new, MODULES.get(module, module), old],
        )
    protected = SQL(" AND ").join(
        SQL("name NOT LIKE %s", pattern) for pattern in PROTECTED_NAMES
    )
    for old, new in NAME_TOKENS:
        cr.execute(
            SQL(
                """
                UPDATE ir_model_data SET name = replace(name, %s, %s)
                 WHERE position(%s in name) > 0 AND %s
                   AND model != 'ir.model.fields'
                   AND NOT EXISTS (
                       SELECT 1 FROM ir_model_data clash
                        WHERE clash.module = ir_model_data.module
                          AND clash.name = replace(ir_model_data.name, %s, %s)
                   )
                """,
                old,
                new,
                old,
                protected,
                old,
                new,
            )
        )
    for old, new in TABLES.items():
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s || substring(name from %s)
             WHERE model = 'ir.model.fields' AND name LIKE %s
            """,
            [f"field_{new}", len(f"field_{old}") + 1, f"field_{old}\\_\\_%"],
        )
    if schema.table_exists(cr, "ir_model_constraint"):
        for old, new in TABLES.items():
            cr.execute(
                """
                UPDATE ir_model_constraint SET name = %s || substring(name from %s)
                 WHERE name LIKE %s
                """,
                [new, len(old) + 1, old + "\\_%"],
            )


def _rename_config_parameters(cr):
    cut = len("api_transport.") + 1
    cr.execute(
        r"""
        UPDATE ir_config_parameter
           SET key = 'integration.' || substring(key from %s)
         WHERE key LIKE 'api\_transport.%%'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter existing
                WHERE existing.key =
                      'integration.' || substring(ir_config_parameter.key from %s)
           )
        """,
        [cut, cut],
    )


def _rename_job_channels(cr):
    if not schema.table_exists(cr, "ir_job_channel"):
        return
    for old, new in JOB_CHANNELS.items():
        cr.execute(
            """
            UPDATE ir_job_channel SET name = %s WHERE name = %s
               AND NOT EXISTS (SELECT 1 FROM ir_job_channel WHERE name = %s)
            """,
            [new, old, new],
        )
        if schema.table_exists(cr, "ir_job") and schema.column_exists(
            cr, "ir_job", "channel"
        ):
            cr.execute("UPDATE ir_job SET channel = %s WHERE channel = %s", [new, old])


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = 'api_transport'")
    if not cr.fetchone():
        return
    _rename_model_tables(cr)
    _rename_many2many(cr)
    _repoint_model_names(cr)
    _rewrite_reference_values(cr)
    _rewrite_expressions(cr)
    _rename_modules(cr)
    _rename_xml_ids(cr)
    _rename_config_parameters(cr)
    _rename_job_channels(cr)
