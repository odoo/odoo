# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TestModel(models.Model):
    _name = 'test.model'
    _inherit = [
        'website.seo.metadata',
        'website.published.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Website Model Test'

    name = fields.Char(required=1)

    @api.model
    def _search_get_detail(self, website, order, options):
        return {
            'model': 'test.model',
            'base_domain': [],
            'search_fields': ['name'],
            'fetch_fields': ['name'],
            'mapping': {
                'name': {'name': 'name', 'type': 'text', 'match': True},
                'website_url': {'name': 'name', 'type': 'text', 'truncate': False},
            },
            'icon': 'fa-check-square-o',
            'order': 'name asc, id desc',
        }

    def open_website_url(self):
        self.ensure_one()
        return self.env['website'].get_client_action(f'/test_model/{self.id}')


class TestModelMultiWebsite(models.Model):
    _name = 'test.model.multi.website'
    _inherit = [
        'website.published.multi.mixin',
    ]
    _description = 'Multi Website Model Test'

    name = fields.Char(required=1)
    # `cascade` is needed as there is demo data for this model which are bound
    # to website 2 (demo website). But some tests are unlinking the website 2,
    # which would fail if the `cascade` is not set. Note that the website 2 is
    # never set on any records in all other modules.
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')
