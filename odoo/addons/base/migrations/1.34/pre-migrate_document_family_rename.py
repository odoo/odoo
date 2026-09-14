from odoo.db import schema
from odoo.tools import SQL

MODULES = {
    "ai_documents": "ai_document",
    "ai_documents_account": "ai_document_account",
    "ai_documents_source": "ai_document_source",
    "documents": "document",
    "documents_account": "document_account",
    "documents_account_peppol": "document_account_peppol",
    "documents_compliance": "document_compliance",
    "documents_custody": "document_custody",
    "documents_enterprise": "document_enterprise",
    "documents_fleet": "document_fleet",
    "documents_fsm": "document_fsm",
    "documents_hr": "document_hr",
    "documents_hr_expense": "document_hr_expense",
    "documents_hr_holidays": "document_hr_holidays",
    "documents_hr_payroll": "document_hr_payroll",
    "documents_l10n_be_hr_payroll": "document_l10n_be_hr_payroll",
    "documents_l10n_ch_hr_payroll": "document_l10n_ch_hr_payroll",
    "documents_l10n_hk_hr_payroll": "document_l10n_hk_hr_payroll",
    "documents_l10n_ke_hr_payroll": "document_l10n_ke_hr_payroll",
    "documents_l10n_mx_edi": "document_l10n_mx_edi",
    "documents_product": "document_product",
    "documents_product_asset": "document_product_asset",
    "documents_product_asset_compliance": "document_product_asset_compliance",
    "documents_product_asset_compliance_hr": "document_product_asset_compliance_hr",
    "documents_project": "document_project",
    "documents_project_sale": "document_project_sale",
    "documents_project_sign": "document_project_sign",
    "documents_sign": "document_sign",
    "documents_speech": "document_speech",
    "documents_spreadsheet": "document_spreadsheet",
    "documents_spreadsheet_survey": "document_spreadsheet_survey",
    "spreadsheet_dashboard_documents": "spreadsheet_dashboard_document",
    "test_documents_full": "test_document_full",
    "website_documents": "website_document",
}

MODELS = {
    "ai_documents.sort": "ai_document.sort",
    "documents.access": "document.access",
    "documents.access.log": "document.access.log",
    "documents.access.tracking": "document.access.tracking",
    "documents.account.folder.setting": "document.account.folder.setting",
    "documents.compliance.report": "document.compliance.report",
    "documents.document": "document.document",
    "documents.link_to_record_wizard": "document.link_to_record_wizard",
    "documents.location": "document.location",
    "documents.move": "document.move",
    "documents.mx_edi_to_record_line": "document.mx_edi_to_record_line",
    "documents.mx_edi_to_record_wizard": "document.mx_edi_to_record_wizard",
    "documents.operation": "document.operation",
    "documents.redirect": "document.redirect",
    "documents.request_wizard": "document.request_wizard",
    "documents.sharing": "document.sharing",
    "documents.sharing.access": "document.sharing.access",
    "documents.tag": "document.tag",
    "documents.transfer.register": "document.transfer.register",
    "documents.transfer.register.line": "document.transfer.register.line",
    "documents.type": "document.type",
}

OLD_MODELS = list(MODELS)
NEW_MODELS = [MODELS[m] for m in OLD_MODELS]

TABLES = dict(
    sorted(
        ((o.replace(".", "_"), n.replace(".", "_")) for o, n in MODELS.items()),
        key=lambda kv: -len(kv[0]),
    )
)

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
        cr.execute("UPDATE ir_module_module SET name = %s WHERE name = %s", [new, old])
        cr.execute(
            "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
            [new, old],
        )
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s
             WHERE module = 'base' AND model = 'ir.module.module' AND name = %s
            """,
            [f"module_{new}", f"module_{old}"],
        )


def _rename_derived_xml_ids(cr):
    for old, new in TABLES.items():
        cr.execute(
            "UPDATE ir_model_data SET name = %s WHERE model = 'ir.model' AND name = %s",
            [f"model_{new}", f"model_{old}"],
        )
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s || substring(name from %s)
             WHERE model = 'ir.model.fields' AND name LIKE %s
            """,
            [f"field_{new}", len(f"field_{old}") + 1, f"field_{old}\\_\\_%"],
        )
        if schema.table_exists(cr, "ir_model_constraint"):
            cr.execute(
                """
                UPDATE ir_model_constraint SET name = %s || substring(name from %s)
                 WHERE name LIKE %s
                """,
                [new, len(old) + 1, old + "\\_%"],
            )


def _rename_config_parameters(cr):
    cut = len("documents.") + 1
    cr.execute(
        r"""
        UPDATE ir_config_parameter
           SET key = 'document.' || substring(key from %s)
         WHERE key LIKE 'documents.%%'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter existing
                WHERE existing.key =
                      'document.' || substring(ir_config_parameter.key from %s)
           )
        """,
        [cut, cut],
    )


def migrate(cr, version):
    if not version:
        return
    _rename_model_tables(cr)
    _rename_many2many(cr)
    _repoint_model_names(cr)
    _rewrite_expressions(cr)
    _rename_modules(cr)
    _rename_derived_xml_ids(cr)
    _rename_config_parameters(cr)
