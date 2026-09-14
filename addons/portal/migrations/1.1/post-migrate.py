"""Take share invitations out of the document threads they were posted to.

``portal.share`` used to post each invitation as a note on the shared record, so
the recipient's credential in it -- a signup token, or the ``pid``/``hash`` pair
that posts as them -- was readable by everyone who could read the record, and the
pair never expires. The wizard now sends a ``user_notification``, which only its
author and recipients can read; the messages already posted become one too, so
they leave the chatter while every recipient keeps their copy.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE mail_message message
           SET message_type = 'user_notification'
         WHERE message.message_type = 'notification'
           AND message.subtype_id = (
                   SELECT res_id FROM ir_model_data
                    WHERE module = 'mail' AND name = 'mt_note'
               )
           AND EXISTS (
                   SELECT 1 FROM mail_message_res_partner_rel recipient
                    WHERE recipient.mail_message_id = message.id
               )
           AND (
                   (message.body LIKE %s AND message.body LIKE %s)
                OR (message.body LIKE %s AND message.body LIKE %s)
               )
        """,
        ("%/web/signup?%", "%token=%", "%pid=%", "%hash=%"),
    )
    _logger.info(
        "portal: %s share invitation(s) moved out of document threads", cr.rowcount
    )
