from __future__ import annotations

from odoo import models


class IrHttp(models.AbstractModel):
    """Expose the user dialog size preference through the session info."""

    _inherit = 'ir.http'

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def session_info(self) -> dict:
        """Add the current user dialog size to the session info payload."""
        result = super().session_info()
        result['dialog_size'] = self.env.user.dialog_size
        return result
