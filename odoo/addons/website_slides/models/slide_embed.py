# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'website_name'

    slide_id = fields.Many2one(
        'slide.slide', string="Presentation",
        required=True, index=True, ondelete='cascade')
    url = fields.Char('Third Party Website URL')
    website_name = fields.Char('Website', compute='_compute_website_name')
    count_views = fields.Integer('# Views', default=1)

    @api.depends('url')
    def _compute_website_name(self):
        for slide_embed in self:
            slide_embed.website_name = slide_embed.url or _('Unknown Website')
