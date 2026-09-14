from odoo.db import schema
from odoo.tools import SQL

MODULES = {"api_ai_agent": "ai_gateway_ml"}


def _rename_module(cr, old, new):
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


def migrate(cr, version):
    if not version:
        return
    for old, new in MODULES.items():
        cr.execute("SELECT 1 FROM ir_module_module WHERE name = %s", [old])
        if cr.fetchone():
            _rename_module(cr, old, new)
