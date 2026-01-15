# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_parse

from odoo.tests.common import HttpCase


class TestWebRedirect(HttpCase):
    def setUp(self):
        super().setUp()

    def test_web_route_redirect_param_legacy(self):
        # This test is for legacy routes with /web and fragement
        web_response = self.url_open('/web#cids=1&action=887&menu_id=124')
        web_response.raise_for_status()
        response_url_query = url_parse(web_response.url).query

        self.assertEqual(response_url_query, 'redirect=%2Fweb%3F')

    def test_web_route_redirect_param(self):
        # This test if for the new routes with /odoo, pathname and query params
        web_response = self.url_open('/odoo/action-887?cids=1')
        web_response.raise_for_status()
        response_url_query = url_parse(web_response.url).query

        self.assertEqual(response_url_query, 'redirect=%2Fodoo%2Faction-887%3Fcids%3D1')
