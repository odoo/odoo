import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Make room for UNIQUE (identifier, company_id) NULLS NOT DISTINCT.

    company_id only defaults to the current company, so a device written without one
    escaped the identifier check entirely. A device is a physical thing with data
    hanging off it, so this refuses rather than deleting one."""
    if not version:
        return

    cr.execute(
        """
        SELECT identifier, company_id, array_agg(id ORDER BY id) AS ids
          FROM remote_device
         WHERE company_id IS NULL
         GROUP BY identifier, company_id
        HAVING COUNT(*) > 1
        """
    )
    groups = cr.fetchall()
    if not groups:
        _logger.info("remote.device: no duplicates, the key is free to tighten")
        return

    raise ValueError(
        "remote.device cannot tighten its natural key: "
        + "; ".join(f"{tuple(key)} is held by ids {ids}" for *key, ids in groups)
        + ". Two devices with no company share an identifier, which is how a device is addressed. Give them their companies, or retire the one that is gone, then update again."
    )
