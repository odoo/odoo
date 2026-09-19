from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "project_baseline_line", ["project_id"])
    schema.drop_columns(cr, "project_retrospective_action", ["project_id"])
    schema.drop_columns(cr, "project_task_dependency", ["project_id"])
