from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "res_company", ["l10n_in_pan_entity_id"])
