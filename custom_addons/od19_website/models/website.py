import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Odoo ships the website record as "My Website", which then leaks into every
# browser tab as "<page name> | My Website".  Brand it on install/upgrade.
DEFAULT_NAME = "My Website"
WEBSITE_NAME = "Auto-Info"


class Website(models.Model):
    _inherit = "website"

    @api.model
    def od19_setup_website(self):
        """Brand the default website (idempotent)."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website or website.name != DEFAULT_NAME:
            return
        website.sudo().write({"name": WEBSITE_NAME})
        _logger.info("od19_website: renamed default website to %r", WEBSITE_NAME)
