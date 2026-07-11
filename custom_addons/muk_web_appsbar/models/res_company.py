from __future__ import annotations

from odoo import fields, models


class ResCompany(models.Model):
    """Add the appbar footer image to companies."""

    _inherit = 'res.company'

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    appbar_image = fields.Binary(
        string='Apps Menu Footer Image',
        attachment=True,
    )
