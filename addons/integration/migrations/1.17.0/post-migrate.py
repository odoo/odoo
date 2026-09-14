import logging

_logger = logging.getLogger(__name__)

MAIL_MODELS = ["integration.exchange", "integration.service", "credential.credential"]


def migrate(cr, version):
    if not version:
        return

    cr.execute("SELECT to_regclass('mail_message')")
    if cr.fetchone()[0] is None:
        return

    cr.execute("DELETE FROM mail_message WHERE model = ANY(%s)", (MAIL_MODELS,))
    messages = cr.rowcount

    cr.execute("DELETE FROM mail_followers WHERE res_model = ANY(%s)", (MAIL_MODELS,))
    followers = cr.rowcount

    cr.execute(
        """
        DELETE FROM mail_activity
        WHERE res_model = 'credential.credential'
          AND summary = 'API credential expiring'
        """,
    )
    activities = cr.rowcount

    _logger.info(
        "integration 19.0.1.17.0: dropped the mail dependency and swept "
        "%d mail_message, %d mail_followers and %d mail_activity rows it left "
        "behind",
        messages,
        followers,
        activities,
    )
