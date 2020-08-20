# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from PIL import Image

from odoo import api, fields, models
from odoo.tools import ImageProcess


class Website(models.Model):
    _inherit = "website"

    app_icon = fields.Image(string='Website App Icon', compute='_compute_app_icon', store=True, readonly=True, help='This field holds the image used as mobile app icon on the website (PNG format).')

    @api.depends('favicon')
    def _compute_app_icon(self):
        """ Computes a squared image based on the favicon to be used as mobile webapp icon.
            App Icon should be in PNG format and size of at least 512x512.
        """
        for website in self:
            image = ImageProcess(website.favicon)
            w, h = image.image.size
            square_size = w if w > h else h
            image.crop_resize(square_size, square_size)
            image.image = image.image.resize((512, 512))
            image.operationsCount += 1
            website.app_icon = image.image_base64(output_format='PNG')
