from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "forum_post_vote", ["forum_id", "recipient_id"])
