# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from ..fields import FSImage


class FSImageMixin(models.AbstractModel):
    _name = "fs.image.mixin"
    _description = "Image Mixin"

    image = FSImage("Image")
    # resized fields stored (as attachment) for performance
    image_medium = FSImage(
        "Image medium", related="image", max_width=128, max_height=128, store=True
    )
