import logging

from odoo import api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    subtype = env.ref("purchase.mt_rfq_approved", raise_if_not_found=False)
    if not subtype:
        return
    subtype.unlink()
    _logger.info(
        "purchase 1.9: removed the mt_rfq_approved mail subtype, which nothing "
        "posts since approval moved to approval_purchase",
    )
