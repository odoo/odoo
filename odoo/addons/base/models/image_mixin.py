# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


class ImageMixin(models.AbstractModel):
    _name = 'image.mixin'
    _description = "Image Mixin"

    # all image fields are base64 encoded and PIL-supported

    image_original = fields.Image("Original Image", help="Image in its original size, as it was uploaded.")

    # resized fields stored (as attachment) for performance
    image_big = fields.Image("Big-sized Image", related="image_original", max_width=1024, max_height=1024, store=True, help="1024px * 1024px")
    image_large = fields.Image("Large-sized Image", related="image_original", max_width=256, max_height=256, store=True, help="256px * 256px")
    image_medium = fields.Image("Medium-sized Image", related="image_original", max_width=128, max_height=128, store=True, help="128px * 128px")
    image_small = fields.Image("Small-sized Image", related="image_original", max_width=64, max_height=64, store=True, help="64px * 64px")

    can_image_be_zoomed = fields.Boolean("Can image raw be zoomed", compute='_compute_images', store=True)

    image = fields.Image("Image", compute='_compute_image', inverse='_set_image')

    @api.depends('image_original')
    def _compute_images(self):
        for record in self:
            image = record.image_original
            record.can_image_be_zoomed = image and tools.is_image_size_above(image)

    @api.depends('image_big')
    def _compute_image(self):
        for record in self:
            record.image = record.image_big

    def _set_image(self):
        for record in self:
            record.image_original = record.image
        # We want the image field to be recomputed to have a correct size.
        # Without this `invalidate_cache`, the image field will keep holding the
        # image_original instead of the big-sized image.
        self.invalidate_cache()
