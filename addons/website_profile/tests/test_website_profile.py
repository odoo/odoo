# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.gamification.tests.common import HttpCaseGamification
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_profile.controllers.main import WebsiteProfile


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteProfile(HttpCaseGamification):
    def test_prepare_url_from_info(self):
        controller = WebsiteProfile()
        base_url = self.base_url()
        base_url_other = 'https://other-domain.com'
        no_url_from = {'url_from': None, 'url_from_label': None}
        for referer, expected in (
            ('/forum?p=1#f=2', {'url_from': '/forum?p=1#f=2', 'url_from_label': 'Forum'}),
            ('/forum/test?p=1#f=2', {'url_from': '/forum/test?p=1#f=2', 'url_from_label': 'Forum'}),
            ('/slides?p=1#f=2', {'url_from': '/slides?p=1#f=2', 'url_from_label': 'All Courses'}),

            ('/profile', no_url_from),
            (None, no_url_from),
        ):
            with (MockRequest(self.env, url_root=base_url, path='/profile/user/1') as mock_request,
                  self.subTest(referer=referer)):
                mock_request.httprequest.headers = {'Referer': f'{base_url}{referer}' if referer else None}
                expected_with_base_url = {
                    'url_from': f'{base_url}{expected["url_from"]}' if expected.get("url_from") else None,
                    'url_from_label': expected["url_from_label"],
                }
                self.assertEqual(controller._prepare_url_from_info(), expected_with_base_url)

                mock_request.httprequest.headers = {'Referer': f'{base_url_other}{referer}' if referer else None}
                self.assertEqual(controller._prepare_url_from_info(), {'url_from': None, 'url_from_label': None})

    def test_save_change_description(self):
        odoo.tests.new_test_user(
            self.env, 'test_user',
            karma=100, website_published=True
        )
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        self.start_tour("/", 'website_profile_description', login="admin")
