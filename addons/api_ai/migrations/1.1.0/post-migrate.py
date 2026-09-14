import logging

_logger = logging.getLogger(__name__)

_SELF_VERSIONED_CODES = ("claude", "gemini")


def migrate(cr, version):
    cr.execute(
        """
        UPDATE integration_service
           SET send_version_headers = false
         WHERE code = ANY(%s)
           AND send_version_headers IS DISTINCT FROM false
        """,
        (list(_SELF_VERSIONED_CODES),),
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.1.0: %s service(s) of %s opted out of the generic version "
            "headers they were excluded from in code before this field existed.",
            cr.rowcount,
            ", ".join(_SELF_VERSIONED_CODES),
        )
