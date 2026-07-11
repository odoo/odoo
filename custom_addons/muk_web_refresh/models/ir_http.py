from __future__ import annotations

from odoo import models


class IrHttp(models.AbstractModel):
    """Expose the configured pager auto-load interval to the web client."""

    _inherit = 'ir.http'

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def session_info(self) -> dict:
        """Add the pager auto-load interval to the session information."""
        result = super().session_info()
        result['pager_autoload_interval'] = int(
            self.env['ir.config_parameter']
            .sudo()
            .get_param(
                'muk_web_refresh.pager_autoload_interval',
                default=30000,
            )
        )
        return result
