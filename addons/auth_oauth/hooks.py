import logging

from odoo import tools

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    Initializing column totp_secret on table res_users
    """
    _logger.info("Initializing column totp_secret on table res_users")
    cr.execute(
        """
        ALTER TABLE res_users ADD COLUMN IF NOT EXISTS totp_secret varchar;
        """
    )
