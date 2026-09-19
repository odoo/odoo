from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "document_document", ["shortcut_document_owner_id"])
