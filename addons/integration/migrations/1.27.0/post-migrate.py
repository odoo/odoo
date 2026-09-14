import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

TEMPLATE_URL = "https://api.example.com"


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    service = env.ref("integration.service_custom_api", raise_if_not_found=False)
    if not service:
        return
    in_use = service.credential_ids or service.connection_ids
    if in_use or service.endpoint_url != TEMPLATE_URL:
        _logger.info(
            "integration: kept service %s (%s): it is configured or has credentials, "
            "so it is no longer the seeded template",
            service.code,
            service.id,
        )
        return
    service.unlink()
