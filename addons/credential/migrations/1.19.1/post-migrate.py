from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "credential_credential", ["category_code"])
    schema.drop_columns(cr, "credential_use", ["company_id"])
