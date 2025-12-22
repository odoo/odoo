# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import Command
from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('post_install', '-at_install')
class TestGetCurrentWebsite(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')

    def test_01_get_current_website_id(self):
        """Make sure `_get_current_website_id works`."""

        Website = self.env['website']

        # clean initial state
        website1 = self.website
        website1.domain = False

        website2 = Website.create({'name': 'My Website 2'})

        # CASE: no domain: get first
        self.assertEqual(Website._get_current_website_id(''), website1.id)

        # setup domain
        website1.domain = 'my-site-1.fr'
        website2.domain = 'https://my2ndsite.com:80'

        # CASE: domain set: get matching domain
        self.assertEqual(Website._get_current_website_id('my-site-1.fr'), website1.id)

        # CASE: domain set: get matching domain (scheme and port supported)
        self.assertEqual(Website._get_current_website_id('my-site-1.fr:8069'), website1.id)

        self.assertEqual(Website._get_current_website_id('my2ndsite.com:80'), website2.id)
        self.assertEqual(Website._get_current_website_id('my2ndsite.com:8069'), website2.id)
        self.assertEqual(Website._get_current_website_id('my2ndsite.com'), website2.id)

        # CASE: domain set, wrong domain: get first
        self.assertEqual(Website._get_current_website_id('test.com'), website1.id)

        # CASE: subdomain: not supported
        self.assertEqual(Website._get_current_website_id('www.my2ndsite.com'), website1.id)

        # CASE: domain set: get by domain in priority
        self.assertEqual(Website._get_current_website_id('my2ndsite.com'), website2.id)
        self.assertEqual(Website._get_current_website_id('my-site-1.fr'), website1.id)

        # CASE: overlapping domain: get exact match
        website1.domain = 'site-1.com'
        website2.domain = 'even-better-site-1.com'
        self.assertEqual(Website._get_current_website_id('site-1.com'), website1.id)
        self.assertEqual(Website._get_current_website_id('even-better-site-1.com'), website2.id)

        # CASE: case insensitive
        website1.domain = 'Site-1.com'
        website2.domain = 'Even-Better-site-1.com'
        self.assertEqual(Website._get_current_website_id('sitE-1.com'), website1.id)
        self.assertEqual(Website._get_current_website_id('even-beTTer-site-1.com'), website2.id)

        # CASE: same domain, different port
        website1.domain = 'site-1.com:80'
        website2.domain = 'site-1.com:81'
        self.assertEqual(Website._get_current_website_id('site-1.com:80'), website1.id)
        self.assertEqual(Website._get_current_website_id('site-1.com:81'), website2.id)
        self.assertEqual(Website._get_current_website_id('site-1.com:82'), website1.id)
        self.assertEqual(Website._get_current_website_id('site-1.com'), website1.id)

        # CASE: Unicode domain (IDNA) support
        website2.domain = 'düsseldorf.com'
        self.assertEqual(Website._get_current_website_id('xn--dsseldorf-q9a.com'), website2.id)
        self.assertEqual(Website._get_current_website_id('düsseldorf.com'), website2.id)

        # CASE: domain stored as punycode
        website2.domain = 'xn--dsseldorf-q9a.com'
        self.assertEqual(Website._get_current_website_id('xn--dsseldorf-q9a.com'), website2.id)
        self.assertEqual(Website._get_current_website_id('düsseldorf.com'), website2.id)

    def test_02_signup_user_website_id(self):
        website = self.website
        website.specific_user_account = True

        user = self.env['res.users'].create({
            'website_id': website.id,
            'login': 'sad@mail.com',
            'name': 'Hope Fully',
            'groups_id': [
                Command.link(self.env.ref('base.group_portal').id),
                Command.unlink(self.env.ref('base.group_user').id),
            ],
        })
        self.assertTrue(user.website_id == user.partner_id.website_id == website)

    def test_03_rpc_signin_user_website_id(self):
        def rpc_login_user_demo():
            """
            Login with demo using JSON-RPC
            :return: the user's id or False if login failed
            """
            response = self.url_open('/jsonrpc', data=json.dumps({
                "params": {
                    "service": "common",
                    "method": "login",
                    "args": [self.env.cr.dbname, 'demo', 'demo']
                },
            }), headers={"Content-Type": "application/json"})
            return response.json()['result']

        website1 = self.website
        website1.domain = self.base_url()

        website2 = self.env['website'].create({'name': 'My Website 2'})
        website2.domain = False

        # It should login successfully since the host used in the RPC call is
        # the same as the website set on the user.
        self.user_demo.website_id = website1
        self.assertTrue(rpc_login_user_demo())

        # It should not login since the website set on the user has no domain.
        self.user_demo.website_id = website2
        self.assertFalse(rpc_login_user_demo())

    def test_recursive_current_website(self):
        Website = self.env['website']
        self.env['ir.rule'].create({
            'name': 'Recursion Test',
            'model_id': self.env.ref('website.model_website').id,
            'domain_force': [(1, '=', 1)],
            'groups': [],
        })
        # Ensure the cache is invalidated, it is not needed at the time but some
        # code might one day go through get_current_website_id before reaching
        # this code, making this test useless
        self.env.registry.clear_cache()
        failed = False
        # website is added in ir.rule context only when in frontend
        with MockRequest(self.env, website=self.website):
            try:
                Website.with_user(self.env.ref('base.public_user').id).search([])
            except RecursionError:
                # Do not fail test from here to avoid dumping huge stack.
                failed = True
        if failed:
            self.fail("There should not be a RecursionError")
