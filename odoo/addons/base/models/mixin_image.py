from odoo import fields, models


class MixinImage(models.AbstractModel):
    _name = "mixin.image"
    _description = "Image Mixin"

    image_1920 = fields.Image(
        string="Image",
        max_width=1920,
        max_height=1920,
    )

    image_1024 = fields.Image(
        related="image_1920",
        string="Image 1024",
        max_width=1024,
        max_height=1024,
        store=True,
    )
    image_512 = fields.Image(
        related="image_1920",
        string="Image 512",
        max_width=512,
        max_height=512,
        store=True,
    )
    image_256 = fields.Image(
        related="image_1920",
        string="Image 256",
        max_width=256,
        max_height=256,
        store=True,
    )
    image_128 = fields.Image(
        related="image_1920",
        string="Image 128",
        max_width=128,
        max_height=128,
        store=True,
    )
