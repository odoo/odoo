from __future__ import annotations

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Expose the company appbar image in the general settings."""

    _inherit = 'res.config.settings'

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    appbar_image = fields.Binary(
        related='company_id.appbar_image',
        readonly=False,
    )
