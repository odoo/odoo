from __future__ import annotations

from odoo import fields, models


class ResUsers(models.Model):
    """Add a per-user preference for the chatter position."""

    _inherit = 'res.users'

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        """Allow users to read their own chatter position."""
        return super().SELF_READABLE_FIELDS + [
            'chatter_position',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        """Allow users to write their own chatter position."""
        return super().SELF_WRITEABLE_FIELDS + [
            'chatter_position',
        ]

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    chatter_position = fields.Selection(
        selection=[
            ('side', 'Side'),
            ('bottom', 'Bottom'),
        ],
        string='Chatter Position',
        default='side',
        required=True,
    )
