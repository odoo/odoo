from __future__ import annotations

from odoo import fields, models


class ResCompany(models.Model):
    """Add favicon and apps-menu background-image fields to the company."""

    _inherit = 'res.company'

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    favicon = fields.Binary(
        string='Company Favicon',
        attachment=True,
    )

    background_image = fields.Binary(
        string='Apps Menu Background Image',
        attachment=True,
    )
