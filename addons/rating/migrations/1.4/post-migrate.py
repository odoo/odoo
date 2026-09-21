from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    # 1.2 as published on origin dropped this; a database upgraded here under
    # the 1.2 the rating_id column fill carried before the 2026-09-20
    # renumbering never ran it. Re-issued so every database converges.
    schema.drop_columns(cr, "rating_rating", ["is_internal"])
