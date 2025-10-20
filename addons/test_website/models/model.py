# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class Website(models.Model):
    _inherit = "website"

    name_translated = fields.Char(translate=True)


class TestModel(models.Model):
    _name = 'test.model'
    _inherit = [
        'website.seo.metadata',
        'website.published.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Website Model Test'

    name = fields.Char(required=True, translate=True)
    submodel_ids = fields.One2many('test.submodel', 'test_model_id', "Submodels")
    website_description = fields.Html(
        string="Description for the website",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
        default="""<div class="o_test_website_description"><p>A simple website description content.</p></div>""",
    )
    tag_id = fields.Many2one('test.tag')

    @api.model
    def _search_get_detail(self, website, order, options):
        return {
            'model': 'test.model',
            'base_domain': [],
            'search_fields': ['name', 'submodel_ids.name', 'submodel_ids.tag_id.name'],
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


class TestSubModel(models.Model):
    _name = 'test.submodel'
    _description = 'Website Submodel Test'

    name = fields.Char(required=True)
    test_model_id = fields.Many2one('test.model')
    tag_id = fields.Many2one('test.tag')


class TestTag(models.Model):
    _name = 'test.tag'
    _description = 'Website Tag Test'

    name = fields.Char(required=True)


class TestModelMultiWebsite(models.Model):
    _name = 'test.model.multi.website'
    _inherit = [
        'website.published.multi.mixin',
    ]
    _description = 'Multi Website Model Test'

    name = fields.Char(required=True)
    # `cascade` is needed as there is demo data for this model which are bound
    # to website 2 (demo website). But some tests are unlinking the website 2,
    # which would fail if the `cascade` is not set. Note that the website 2 is
    # never set on any records in all other modules.
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')


class TestModelExposed(models.Model):
    _name = "test.model.exposed"
    _inherit = [
        'website.seo.metadata',
        'website.published.mixin',
    ]
    _description = 'Website Model Test Exposed'
    _rec_name = "name"

    name = fields.Char()
