import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE device_profile SET disconnect_timeout = 0 "
        "WHERE disconnect_timeout = 3600"
    )
    _logger.info(
        "19.0.1.6.0: %s profile(s) still on the old 3600s default now inherit "
        "the global disconnect timeout",
        cr.rowcount,
    )
