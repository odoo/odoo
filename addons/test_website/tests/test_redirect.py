# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.http_routing.models.ir_http import slug


@tagged('-at_install', 'post_install')
class TestRedirect(HttpCase):

    def setUp(self):
        super(TestRedirect, self).setUp()

        self.user_portal = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Test Website Portal User',
            'login': 'portal_user',
            'password': 'portal_user',
            'email': 'portal_user@mail.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.redirect = self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/test_website/country/<model("res.country"):country>',
            'url_to': '/redirected/country/<model("res.country"):country>',
        })
        self.country_ad = self.env.ref('base.ad')

    def test_01_redirect_308_model_converter(self):
        """ Ensure 308 redirect with model converter works fine, including:
                - Correct & working redirect as public user
                - Correct & working redirect as logged in user
                - Correct replace of url_for() URLs in DOM
        """
        url = '/test_website/country/' + slug(self.country_ad)
        redirect_url = url.replace('test_website', 'redirected')

        # [Public User] Open the original url and check redirect OK
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith(redirect_url), "Ensure URL got redirected")
        self.assertTrue(self.country_ad.name in r.text, "Ensure the controller returned the expected value")
        self.assertTrue(redirect_url in r.text, "Ensure the url_for has replaced the href URL in the DOM")

        # [Logged In User] Open the original url and check redirect OK
        self.authenticate("portal_user", "portal_user")
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith(redirect_url), "Ensure URL got redirected (2)")
        self.assertTrue('Logged In' in r.text, "Ensure logged in")
        self.assertTrue(self.country_ad.name in r.text, "Ensure the controller returned the expected value (2)")
        self.assertTrue(redirect_url in r.text, "Ensure the url_for has replaced the href URL in the DOM")

    def test_02_redirect_308_model_converter_record_not_exist(self):
        # Accessing a 308 route should not crash if the Model Converter record doesn't exist
        r = self.url_open('/test_website/country/whatever-10000')
        self.assertEqual(r.status_code, 404)
