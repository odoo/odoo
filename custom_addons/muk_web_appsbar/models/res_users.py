from __future__ import annotations

from odoo import fields, models


class ResUsers(models.Model):
    """Add the per-user sidebar display preference."""

    _inherit = 'res.users'

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        """Allow users to read their own sidebar type."""
        return super().SELF_READABLE_FIELDS + [
            'sidebar_type',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        """Allow users to write their own sidebar type."""
        return super().SELF_WRITEABLE_FIELDS + [
            'sidebar_type',
        ]

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    sidebar_type = fields.Selection(
        selection=[
            ('invisible', 'Invisible'),
            ('small', 'Small'),
            ('large', 'Large'),
        ],
        string='Sidebar Type',
        default='large',
        required=True,
    )
