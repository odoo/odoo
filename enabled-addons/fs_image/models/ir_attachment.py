# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    alt_text = fields.Char(
        "Alternative Text",
        help="Alternative text for the image. Only used for images on a website.",
        translate=False,
    )
