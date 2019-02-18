# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


class ImageMixin(models.AbstractModel):
    _name = 'image.mixin'
    _description = "Image Mixin"

    # all image fields are base64 encoded and PIL-supported

    # all image_raw fields are technical and should not be displayed to the user
    image_raw_original = fields.Binary("Raw Original Image")

    # resized fields stored (as attachment) for performance
    image_raw_big = fields.Binary("Raw Big-sized Image", compute='_compute_image_raw', store=True)
    image_raw_large = fields.Binary("Raw Large-sized Image", compute='_compute_image_raw', store=True)
    image_raw_medium = fields.Binary("Raw Medium-sized Image", compute='_compute_image_raw', store=True)
    image_raw_small = fields.Binary("Raw Small-sized Image", compute='_compute_image_raw', store=True)
    can_image_raw_be_zoomed = fields.Boolean("Can image raw be zoomed", compute='_compute_image_raw', store=True)

    # Computed fields that are used to create a fallback if necessary, it's
    # recommended to display those fields to the user.
    image_original = fields.Binary("Original Image", compute='_compute_image_original', inverse='_set_image_original', help="Image in its original size, as it was uploaded.")
    image = fields.Binary("Big-sized Image", help="1024px * 1024px", compute='_compute_image', inverse='_set_image')
    image_large = fields.Binary("Large-sized Image", help="256px * 256px", compute='_compute_image_large')
    image_medium = fields.Binary("Medium-sized Image", help="128px * 128px", compute='_compute_image_medium')
    image_small = fields.Binary("Small-sized Image", help="64px * 64px", compute='_compute_image_small')
    can_image_be_zoomed = fields.Boolean("Can image be zoomed", compute='_compute_can_image_be_zoomed')

    @api.multi
    @api.depends('image_raw_original')
    def _compute_image_raw(self):
        for record in self:
            images = tools.image_get_resized_images(record.image_raw_original, big_name=False)
            record.image_raw_big = tools.image_get_resized_images(record.image_raw_original,
                large_name=False, medium_name=False, small_name=False, preserve_aspect_ratio=True)['image']
            record.image_raw_large = images['image_large']
            record.image_raw_medium = images['image_medium']
            record.image_raw_small = images['image_small']
            record.can_image_raw_be_zoomed = tools.is_image_size_above(record.image_raw_original)

    @api.multi
    def _compute_image_original(self):
        for record in self:
            record.image_original = record.image_raw_original or record._get_image_fallback_record().image_raw_original

    @api.multi
    def _set_image_original(self):
        for record in self:
            fallback = record._get_image_fallback_record()
            if (
                # We are trying to remove an image even though it is already
                # not set, remove it from the fallback record instead.
                not record.image_original and not record.image_raw_original or
                # We are trying to add an image, but the fallback image is
                # not set, write on the fallback instead.
                record.image_original and not fallback.image_raw_original or
                # The record using the mixin asks to always write on fallback.
                record._force_write_image_on_fallback()
            ):
                fallback.image_raw_original = record.image_original
            else:
                record.image_raw_original = record.image_original

    @api.multi
    def _compute_image(self):
        for record in self:
            record.image = record.image_raw_big or record._get_image_fallback_record().image_raw_big

    @api.multi
    def _set_image(self):
        for record in self:
            record.image_original = record.image
        # We want the image field to be recomputed to have a correct size.
        # Without this `invalidate_cache`, the image field will keep holding the
        # image_original instead of the big-sized image.
        self.invalidate_cache()

    @api.multi
    def _compute_image_large(self):
        for record in self:
            record.image_large = record.image_raw_large or record._get_image_fallback_record().image_raw_large

    @api.multi
    def _compute_image_medium(self):
        for record in self:
            record.image_medium = record.image_raw_medium or record._get_image_fallback_record().image_raw_medium

    @api.multi
    def _compute_image_small(self):
        for record in self:
            record.image_small = record.image_raw_small or record._get_image_fallback_record().image_raw_small

    @api.multi
    def _compute_can_image_be_zoomed(self):
        for record in self:
            record.can_image_be_zoomed = record.can_image_raw_be_zoomed if record.image_raw_original else record._get_image_fallback_record().can_image_raw_be_zoomed

    @api.multi
    def _get_image_fallback_record(self):
        """Return a record to fallback on when getting an image if the image is
        not set for self.

        The returned record must implement the current mixin, or at least have
        the different ``image_raw`` fields defined on it."""
        self.ensure_one()
        return self

    @api.multi
    def _force_write_image_on_fallback(self):
        """Return whether we should always write the image on the fallback.

        :return: True to always write on the fallback no matter the situation,
            False to write on the current record or on the fallback depending
            on the situation. See `_set_image_original`.
        """
        self.ensure_one()
        return False

    @api.multi
    def unlink(self):
        """If the fallback image is not set, move the current image to the
        fallback."""
        for record in self:
            fallback = record._get_image_fallback_record()
            if fallback != record and record.image_raw_original and not fallback.image_raw_original:
                fallback.image_raw_original = record.image_raw_original
        return super(ImageMixin, self).unlink()
