# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import fields, models


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, index=True)
    url = fields.Char('Third Party Website URL', required=True)
    count_views = fields.Integer('# Views', default=1)

    def _add_embed_url(self, slide_id, url):
        baseurl = urls.url_parse(url).netloc
        if not baseurl:
            return 0
        embeds = self.search([('url', '=', baseurl), ('slide_id', '=', int(slide_id))], limit=1)
        if embeds:
            embeds.count_views += 1
        else:
            embeds = self.create({
                'slide_id': slide_id,
                'url': baseurl,
            })
        return embeds.count_views
