from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "account_move_line", ["l10n_latam_document_type_id"])
