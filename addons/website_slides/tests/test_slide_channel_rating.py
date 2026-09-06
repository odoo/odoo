from markupsafe import Markup

from odoo.addons.website_slides.tests.common import SlidesCase


class TestWebsiteSlidesChannelRating(SlidesCase):

    def test_links_in_reviews_created_by_users_have_seo_rel_attributes(self):
        body = '<p>Check <a href="https://example.com">this</a> out!</p>'
        message = self.slide.message_post(body=Markup(body))
        self.assertEqual(message.body, '<p>Check <a href="https://example.com" rel="nofollow noopener noreferrer ugc">this</a> out!</p>')

    def test_links_in_reviews_updated_by_users_have_seo_rel_attributes(self):
        message = self.slide.message_post(body=Markup('<p>No links</p>'))
        message.write({'body': '<p><a href="https://example.com">click here</a></p>'})
        self.assertEqual(message.body, '<p><a href="https://example.com" rel="nofollow noopener noreferrer ugc">click here</a></p>')
