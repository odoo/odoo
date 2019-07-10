# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


class ImageMixin(models.AbstractModel):
    _name = 'image.mixin'
    _description = "Image Mixin"

    # all image fields are base64 encoded and PIL-supported

    image_original = fields.Binary("Original Image", help="Image in its original size, as it was uploaded.")

    # resized fields stored (as attachment) for performance
    image_big = fields.Binary("Big-sized Image", compute='_compute_images', store=True, help="1024px * 1024px")
    image_large = fields.Binary("Large-sized Image", compute='_compute_images', store=True, help="256px * 256px")
    image_medium = fields.Binary("Medium-sized Image", compute='_compute_images', store=True, help="128px * 128px")
    image_small = fields.Binary("Small-sized Image", compute='_compute_images', store=True, help="64px * 64px")

    can_image_be_zoomed = fields.Boolean("Can image raw be zoomed", compute='_compute_images', store=True)

    image = fields.Binary("Image", compute='_compute_image', inverse='_set_image')

    @api.depends('image_original')
    def _compute_images(self):
        for record in self:
            image = record.image_original
            # for performance: avoid calling unnecessary methods when falsy
            images = image and tools.image_get_resized_images(image, big_name=False)
            record.image_big = image and tools.image_get_resized_images(image,
                large_name=False, medium_name=False, small_name=False)['image']
            record.image_large = image and images['image_large']
            record.image_medium = image and images['image_medium']
            record.image_small = image and images['image_small']
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
