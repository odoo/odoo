# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SocialStreamAttachment(models.Model):
    """ A social.stream.post.image represents an image that was shared with a social.stream.post.
    It only contains the URL of the image on the related social.media. """

    _name = 'social.stream.post.image'
    _description = 'Social Stream Post Image Attachment'

    image_url = fields.Char("Image URL", readonly=True, required=True)
    stream_post_id = fields.Many2one('social.stream.post', string="Stream Post", ondelete="cascade")
