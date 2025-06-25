# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import models, fields, _


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model._name == 'blog.post':
            data = [{
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_2.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Islands'),
                'subtitle': _('Alone in the ocean'),
                'post_date': fields.Date.today() - timedelta(days=1),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_3.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('With a View'),
                'subtitle': _('Awesome hotel rooms'),
                'post_date': fields.Date.today() - timedelta(days=2),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_4.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Skies'),
                'subtitle': _('Taking pictures in the dark'),
                'post_date': fields.Date.today() - timedelta(days=3),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_5.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Satellites'),
                'subtitle': _('Seeing the world from above'),
                'post_date': fields.Date.today() - timedelta(days=4),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_6.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Viewpoints'),
                'subtitle': _('Seaside vs mountain side'),
                'post_date': fields.Date.today() - timedelta(days=5),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_7.jpg\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Jungle'),
                'subtitle': _('Spotting the fauna'),
                'post_date': fields.Date.today() - timedelta(days=6),
                'website_url': "",
            }]
            merged = []
            for index in range(0, max(len(samples), len(data))):
                merged.append({**samples[index % len(samples)], **data[index % len(data)]})
                # merge definitions
            samples = merged
        return samples
