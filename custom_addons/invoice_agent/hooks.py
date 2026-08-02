"""Post-install hooks for the ``invoice_agent`` module.

The deployment exposes the public base URL through the ``URL`` environment
variable (see docker-compose.yml). Odoo's runtime web URL is stored in the
``web.base.url`` system parameter, which Odoo otherwise auto-guesses from the
browser origin on the first admin login. Seeding it explicitly means every
generated link (reports, portals, email templates, API responses) uses the
canonical public URL from day one — including on upgrades.
"""

import logging
import os

from odoo import api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Seed ``web.base.url`` from the ``URL`` environment variable.

    Deliberately runs on every install *and* module upgrade so that changing
    ``URL=`` in ``.env`` and releasing is enough to re-point the ERP.
    """
    base_url = os.environ.get("URL", "").strip()
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        _logger.warning(
            "invoice_agent: URL env is missing or not a valid base URL ('%s') — "
            "leaving web.base.url untouched. Set the URL variable in .env.",
            base_url,
        )
        return

    with api.Environment.manage():
        env = api.Environment(cr, 1, {})
        icp = env["ir.config_parameter"]
        icp.set_param("web.base.url", base_url)
        # Freeze it: unless 'web.base.url.freeze' is set, Odoo overwrites
        # web.base.url with the browser origin on every admin login.
        icp.set_param("web.base.url.freeze", "True")

    _logger.info("invoice_agent: web.base.url set to %s (frozen)", base_url)
