from odoo.db.schema import table_exists
from odoo.tools.module_data import rename_model

RECORD_MODELS = (
    "ir.ui.view",
    "ir.actions.act_window",
    "ir.rule",
    "ir.model.access",
    "ir.ui.menu",
)


def migrate(cr, version):
    if not version:
        return
    if table_exists(cr, "resource_calendar_leaves") and not table_exists(
        cr, "resource_schedule_exception"
    ):
        rename_model(cr, "resource.calendar.leaves", "resource.schedule.exception")
    cr.execute(
        """
        UPDATE ir_model_data d
           SET name = regexp_replace(
                   d.name, 'resource_calendar_leaves?', 'resource_schedule_exception', 'g'
               )
         WHERE d.model = ANY(%s)
           AND d.name ~ 'resource_calendar_leave'
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_data e
                 WHERE e.module = d.module
                   AND e.name = regexp_replace(
                       d.name, 'resource_calendar_leaves?', 'resource_schedule_exception', 'g'
                   )
           )
        """,
        [list(RECORD_MODELS)],
    )
