from odoo.db.schema import column_exists


def migrate(cr, version):
    """rating_id is stored on the message: the column is filled here in SQL so
    the ORM does not recompute every message one batch at a time."""
    if not version or column_exists(cr, "mail_message", "rating_id"):
        return
    cr.execute("ALTER TABLE mail_message ADD COLUMN rating_id integer")
    cr.execute(
        """
        UPDATE mail_message m
           SET rating_id = latest.id
          FROM (
                SELECT DISTINCT ON (message_id) id, message_id
                  FROM rating_rating
                 WHERE message_id IS NOT NULL AND consumed
                 ORDER BY message_id, create_date DESC, id DESC
               ) latest
         WHERE latest.message_id = m.id
        """
    )
