# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsitePageProperties(HttpCase):

    def test_website_page_properties_common(self):
        self.start_tour(self.env["website"].get_client_action_url('/test_view'), 'website_page_properties_common', login='admin')

    def test_website_page_properties_can_publish(self):
        item_id = self.env['test.model'].search([], limit=1).ensure_one().id
        self.start_tour(self.env["website"].get_client_action_url(f'/test_website/model_item/{item_id}'), 'website_page_properties_can_publish', login='admin')

    def test_website_page_properties_website_page(self):
        # Create a website page with a different URL to be tested for dependency
        # tracking
        self.env['website.page'].create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div><a href="/cool-page">Cool page</a></div>',
            'key': 'test.cool_page',
            'url': '/dependency_page',
            'website_id': self.env['website'].search([], limit=1).id,
        })

        self.start_tour(self.env["website"].get_client_action_url('/'), 'website_page_properties_website_page', login='admin')

    def test_website_page_properties_seo_name(self):
        record = self.env['test.model'].create({'name': 'Cool Item'})
        website = self.env.ref('base.default_website')
        PageProperties = self.env['website.page.properties.base']

        properties = PageProperties.create({
            'target_model_id': f'test.model,{record.id}',
            'url': f'/test_website/model_item/{record.id}',
            'website_id': website.id,
        })
        self.assertFalse(properties.can_edit_seo_name, "The URL does not contain the slug of the record")

        properties = PageProperties.create({
            'target_model_id': f'test.model,{record.id}',
            'url': f'/test_website/cool-item-{record.id}',
            'website_id': website.id,
        })
        self.assertTrue(properties.can_edit_seo_name)
        self.assertFalse(properties.seo_name)
        properties.seo_name = 'My Custom Name'
        self.assertEqual(record.seo_name, 'my-custom-name', "The custom URL should be slugified")
        properties.seo_name = ''
        self.assertFalse(record.seo_name, "Emptying the custom URL should restore the default one")

        page = self.env['website.page'].search([('website_id', 'in', (website.id, False))], limit=1)
        properties = self.env['website.page.properties'].create({
            'target_model_id': page.id,
            'website_id': website.id,
        })
        self.assertFalse(properties.can_edit_seo_name, "Pages have a fully customizable URL instead")
