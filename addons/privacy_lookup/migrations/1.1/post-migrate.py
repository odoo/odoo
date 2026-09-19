from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "privacy_lookup_wizard_line", ["res_model"])
