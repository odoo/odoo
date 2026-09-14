"""Take survey invitation copies out of applicant threads.

Inviting an applicant used to post a copy of the invitation email on the
applicant, and the email carries the candidate's ``answer_token``: anyone who could
read the applicant could answer, or read the answers, as the candidate. The copy is
no longer posted; the ones already there become a ``user_notification``, which
leaves them to their author.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE mail_message
           SET message_type = 'user_notification'
         WHERE model = 'hr.applicant'
           AND message_type != 'user_notification'
           AND body LIKE %s
        """,
        ("%answer_token=%",),
    )
    _logger.info(
        "hr_recruitment_survey: %s invitation copies moved out of applicant threads",
        cr.rowcount,
    )
