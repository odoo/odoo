from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    # 1.79 as published on origin dropped this; a database upgraded here under
    # the numbers 1.79 to 1.81 carried before the 2026-09-20 renumbering never
    # ran it. Re-issued so every database converges, whichever path it took.
    schema.drop_columns(cr, "res_partner_identifier", ["company_id"])
