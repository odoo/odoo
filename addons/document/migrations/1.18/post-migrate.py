from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    # 1.16 as published on origin dropped this; a database upgraded here under
    # the 1.16 the is_document_request column fill carried before the
    # 2026-09-20 renumbering never ran it. Re-issued so every database converges.
    schema.drop_columns(cr, "document_document", ["shortcut_document_owner_id"])
