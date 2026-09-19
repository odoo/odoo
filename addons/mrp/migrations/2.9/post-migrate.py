from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "mrp_workcenter", ["time_efficiency"])
    schema.drop_columns(cr, "mrp_workorder", ["production_availability"])
