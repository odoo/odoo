from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "resource_assignment", ["company_id"])
