# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_parse

from odoo.tests.common import HttpCase


class TestWebRedirect(HttpCase):
    def setUp(self):
        super().setUp()
        self.encoded_url_query = "redirect=web%23cids%3D1%26action%3Dmenu"

    def test_root_route_redirect_param(self):
        web_response = self.url_open(f"/?{self.encoded_url_query}")
        web_response.raise_for_status()
        response_url_query = url_parse(web_response.url).query

        self.assertEqual(response_url_query, self.encoded_url_query)

    def test_web_route_redirect_param(self):
        web_response = self.url_open(f"/web?{self.encoded_url_query}")
        web_response.raise_for_status()
        response_url_query = url_parse(web_response.url).query

        self.assertEqual(response_url_query, self.encoded_url_query)
