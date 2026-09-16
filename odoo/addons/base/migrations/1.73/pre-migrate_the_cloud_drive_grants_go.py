import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

MODEL = "cloud.drive.access"
TABLE = "cloud_drive_access"


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT m.id
          FROM ir_model m
         WHERE m.model = %s
           AND m.state != 'manual'
           AND NOT EXISTS (
               SELECT 1
                 FROM ir_model_data d
                 JOIN ir_module_module mm ON mm.name = d.module
                WHERE d.model = 'ir.model' AND d.res_id = m.id
                  AND mm.state IN ('installed', 'to upgrade', 'to install')
           )
        """,
        [MODEL],
    )
    row = cr.fetchone()
    if not row:
        return
    [model_id] = row

    cr.execute("SELECT to_regclass(%s)", [f"public.{TABLE}"])
    [table] = cr.fetchone()
    rows = 0
    if table is not None:
        cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(TABLE)))
        [rows] = cr.fetchone()

    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE (model = 'ir.model' AND res_id = %(id)s)
            OR (model = 'ir.model.fields'
                AND res_id IN (SELECT id FROM ir_model_fields WHERE model_id = %(id)s))
            OR (model = 'ir.model.access'
                AND res_id IN (SELECT id FROM ir_model_access WHERE model_id = %(id)s))
            OR (model = 'ir.rule'
                AND res_id IN (SELECT id FROM ir_rule WHERE model_id = %(id)s))
            OR model = %(model)s
        """,
        {"id": model_id, "model": MODEL},
    )
    cr.execute("DELETE FROM ir_model WHERE id = %s", [model_id])
    if table is not None:
        cr.execute(SQL("DROP TABLE %s", SQL.identifier(TABLE)))
    _logger.info(
        "dropped model %r and its table with %s row(s) of per-user path grants, "
        "at the user's instruction: the module that wrote them is gone from the "
        "addons path and nothing can read them",
        MODEL,
        rows,
    )
