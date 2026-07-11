from __future__ import annotations

from odoo import models


class IrHttp(models.AbstractModel):
    """Expose the user chatter position in the session info."""

    _inherit = 'ir.http'

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def session_info(self) -> dict:
        """Add the user chatter position to the session info."""
        result = super().session_info()
        result['chatter_position'] = self.env.user.chatter_position
        return result
