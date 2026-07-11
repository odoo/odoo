from __future__ import annotations

from odoo import fields, models


class ResUsers(models.Model):
    """Store the per-user dialog size preference."""

    _inherit = 'res.users'

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        """Allow users to read their own dialog size preference."""
        return super().SELF_READABLE_FIELDS + [
            'dialog_size',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        """Allow users to write their own dialog size preference."""
        return super().SELF_WRITEABLE_FIELDS + [
            'dialog_size',
        ]

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    dialog_size = fields.Selection(
        selection=[
            ('minimize', 'Minimize'),
            ('maximize', 'Maximize'),
        ],
        string='Dialog Size',
        default='minimize',
        required=True,
    )
