# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import models, fields, api, _
from odoo.fields import Domain


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    def _prepare_values(self, limit=None, search_domain=None, search_info=None, main_object=None, **options):
        search_domain = search_domain or Domain.TRUE
        search_info = search_info or {}

        if ids := search_info.pop('blogByIds', False):
            search_domain &= Domain("blog_id", "in", ids)
        if ids := search_info.pop('blogByTagIds', False):
            search_domain &= Domain("tag_ids", "in", ids)
        if ids := search_info.pop('blogByAuthorIds', False):
            search_domain &= Domain("author_id", "in", ids)

        return super()._prepare_values(limit=limit, search_domain=search_domain, search_info=search_info, main_object=main_object, **options)

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model._name == 'blog.post':
            data = [{
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_3.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Homeworking'),
                'subtitle': _('How to stay productive'),
                'published_date': fields.Date.today() - timedelta(days=1),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_2.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Smart Homes'),
                'subtitle': _('The control in your hands'),
                'published_date': fields.Date.today() - timedelta(days=2),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_6.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Asia'),
                'subtitle': _('Underrated destinations'),
                'published_date': fields.Date.today() - timedelta(days=3),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_5.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Decoration'),
                'subtitle': _('Stay minimalist'),
                'published_date': fields.Date.today() - timedelta(days=4),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_4.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Technology'),
                'subtitle': _('Improve your everyday life'),
                'published_date': fields.Date.today() - timedelta(days=5),
                'website_url': "",
            }, {
                'cover_properties': '{"background-image": "url(\'/website_blog/static/src/img/cover_7.webp\')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}',
                'name': _('Meetings'),
                'subtitle': _('How to make them relevant'),
                'published_date': fields.Date.today() - timedelta(days=6),
                'website_url': "",
            }]
            merged = []
            for index in range(0, max(len(samples), len(data))):
                merged.append({**samples[index % len(samples)], **data[index % len(data)]})
                # merge definitions
            samples = merged
        return samples

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if 'field_names' in defaults and self.env.context.get('model') == 'blog.post':
            defaults['field_names'] = 'name,teaser,subtitle'
        return defaults
