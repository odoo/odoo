import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("SELECT to_regclass('api_credential_wizard')")
    if cr.fetchone()[0] is None:
        return

    cr.execute("DROP TABLE api_credential_wizard")
    _logger.info(
        "integration 19.0.1.15.0: dropped api_credential_wizard, the table of "
        "a wizard nothing could open",
    )
