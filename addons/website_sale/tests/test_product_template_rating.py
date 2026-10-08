from markupsafe import Markup

from odoo.tests import common


class TestWebsiteSaleProductTemplateRating(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Product',
            'website_published': True,
        })

    def test_links_in_reviews_created_by_users_have_seo_rel_attributes(self):
        body = '<p>Check <a href="https://example.com">this</a> product</p>'
        message = self.product_template.message_post(body=Markup(body))
        self.assertEqual(message.body, '<p>Check <a href="https://example.com" rel="nofollow noopener noreferrer ugc">this</a> product</p>')

    def test_links_in_reviews_updated_by_users_have_seo_rel_attributes(self):
        message = self.product_template.message_post(body=Markup('<p>No links</p>'))
        message.write({'body': '<p><a href="https://example.com">click here</a></p>'})
        self.assertEqual(message.body, '<p><a href="https://example.com" rel="nofollow noopener noreferrer ugc">click here</a></p>')
