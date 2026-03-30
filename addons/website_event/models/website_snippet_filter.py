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

        if ids_by_category := search_info.pop('eventByTagIds', False):
            search_domain &= Domain.AND([Domain("tag_ids", "in", ids) for category_id, ids in ids_by_category.items()])

        return super()._prepare_values(limit=limit, search_domain=search_domain, search_info=search_info, main_object=main_object, **options)

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model._name == 'event.event':
            data = [{
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_1.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('Great Reno Ballon Race'),
                'date_begin': fields.Date.today() + timedelta(days=10),
                'date_end': fields.Date.today() + timedelta(days=11),
            }, {
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_2.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('Conference For Architects'),
                'date_begin': fields.Date.today(),
                'date_end': fields.Date.today() + timedelta(days=2),
            }, {
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_3.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('Live Music Festival'),
                'date_begin': fields.Date.today() + timedelta(weeks=8),
                'date_end': fields.Date.today() + timedelta(weeks=8, days=5),
            }, {
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_5.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('Hockey Tournament'),
                'date_begin': fields.Date.today() + timedelta(days=7),
                'date_end': fields.Date.today() + timedelta(days=7),
            }, {
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_7.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('OpenWood Collection Online Reveal'),
                'date_begin': fields.Date.today() + timedelta(days=1),
                'date_end': fields.Date.today() + timedelta(days=3),
            }, {
                'cover_properties': '{"background-image": "url(\'/website_event/static/src/img/event_cover_4.jpg\')", "resize_class": "o_record_has_cover cover_auto", "opacity": "0.4"}',
                'name': _('Business Workshops'),
                'date_begin': fields.Date.today() + timedelta(days=2),
                'date_end': fields.Date.today() + timedelta(days=4),
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
        if 'field_names' in defaults and self.env.context.get('model') == 'event.event':
            defaults['field_names'] = 'name,subtitle'
        return defaults
