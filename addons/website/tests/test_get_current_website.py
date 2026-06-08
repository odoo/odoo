# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.http_routing.tests.common import MockRequest


@tagged('post_install', '-at_install')
class TestGetCurrentWebsite(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('base.default_website')

    def test_01_get_host_id_from_domain(self):
        """Make sure `_get_host_id_from_domain works`."""

        Website = self.env['website']
        irHttp = self.env["ir.http"]

        # clean initial state
        website1 = self.website
        website1.domain = False

        website2 = Website.create({'name': 'My Website 2'})

        # CASE: no domain: get first
        self.assertEqual(irHttp._get_host_id_from_domain(''), website1.id)

        # setup domain
        website1.domain = 'my-site-1.fr'
        website2.domain = 'https://my2ndsite.com:80'

        # CASE: domain set: get matching domain
        self.assertEqual(irHttp._get_host_id_from_domain('my-site-1.fr'), website1.id)

        # CASE: domain set: get matching domain (scheme and port supported)
        self.assertEqual(irHttp._get_host_id_from_domain('my-site-1.fr:8069'), website1.id)

        self.assertEqual(irHttp._get_host_id_from_domain('my2ndsite.com:80'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('my2ndsite.com:8069'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('my2ndsite.com'), website2.id)

        # CASE: domain set, wrong domain: get first
        self.assertEqual(irHttp._get_host_id_from_domain('test.com'), website1.id)

        # CASE: subdomain: not supported
        self.assertEqual(irHttp._get_host_id_from_domain('www.my2ndsite.com'), website1.id)

        # CASE: domain set: get by domain in priority
        self.assertEqual(irHttp._get_host_id_from_domain('my2ndsite.com'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('my-site-1.fr'), website1.id)

        # CASE: overlapping domain: get exact match
        website1.domain = 'site-1.com'
        website2.domain = 'even-better-site-1.com'
        self.assertEqual(irHttp._get_host_id_from_domain('site-1.com'), website1.id)
        self.assertEqual(irHttp._get_host_id_from_domain('even-better-site-1.com'), website2.id)

        # CASE: case insensitive
        website1.domain = 'Site-1.com'
        website2.domain = 'Even-Better-site-1.com'
        self.assertEqual(irHttp._get_host_id_from_domain('sitE-1.com'), website1.id)
        self.assertEqual(irHttp._get_host_id_from_domain('even-beTTer-site-1.com'), website2.id)

        # CASE: same domain, different port
        website1.domain = 'site-1.com:80'
        website2.domain = 'site-1.com:81'
        self.assertEqual(irHttp._get_host_id_from_domain('site-1.com:80'), website1.id)
        self.assertEqual(irHttp._get_host_id_from_domain('site-1.com:81'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('site-1.com:82'), website1.id)
        self.assertEqual(irHttp._get_host_id_from_domain('site-1.com'), website1.id)

        # CASE: Unicode domain (IDNA) support
        website2.domain = 'düsseldorf.com'
        self.assertEqual(irHttp._get_host_id_from_domain('xn--dsseldorf-q9a.com'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('düsseldorf.com'), website2.id)

        # CASE: domain stored as punycode
        website2.domain = 'xn--dsseldorf-q9a.com'
        self.assertEqual(irHttp._get_host_id_from_domain('xn--dsseldorf-q9a.com'), website2.id)
        self.assertEqual(irHttp._get_host_id_from_domain('düsseldorf.com'), website2.id)

    def test_04_http_website_id_sequence(self):
        """Verify the default website updates after changing website sequence."""
        irHttp = self.env["ir.http"]
        Website = self.env['website']
        website1 = self.website
        website1.domain = False
        website2 = Website.create({'name': 'My Website 2', 'domain': False})
        website1.sequence = 10
        website2.sequence = 20

        self.assertEqual(irHttp._get_host_id_from_domain(''), website1.id)

        website2.sequence = 5
        self.assertEqual(irHttp._get_host_id_from_domain(''), website2.id)

    def test_02_signup_user_website_id(self):
        website = self.website
        website.specific_user_account = True

        user = self.env['res.users'].create({
            'website_id': website.id,
            'login': 'sad@mail.com',
            'name': 'Hope Fully',
            'group_ids': [
                Command.link(self.env.ref('base.group_portal').id),
                Command.unlink(self.env.ref('base.group_user').id),
            ],
        })
        self.assertTrue(user.website_id == user.partner_id.website_id == website)

    @mute_logger('odoo.addons.rpc.controllers.jsonrpc')
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
        website1.domain = 'http://[99::99:99:99]:8080/bidule'

        website2 = self.env['website'].create({'name': 'My Website 2'})
        website2.domain = self.base_url()

        website3 = self.env['website'].create({'name': 'My Website 3'})
        website3.domain = False

        # It should not login since the website set on the user has other domain.
        self.user_demo.website_id = website1
        self.assertFalse(rpc_login_user_demo(), 'It should not login since the website set on the user has other domain.')

        # It should login successfully since the host used in the RPC call is
        # the same as the website set on the user.
        self.user_demo.website_id = website2
        self.assertTrue(rpc_login_user_demo(), 'It should login successfully')

        # It should not login since the website set on the user has no domain.
        self.user_demo.website_id = website3
        self.assertFalse(rpc_login_user_demo(), 'It should not login since the website set on the user has no domain.')

    def test_recursive_current_website(self):
        Website = self.env['website']
        self.env['ir.access'].create({
            'name': 'Recursion Test',
            'model_id': self.env.ref('website.model_website').id,
            'operation': 'crud',
        })
        # Ensure the cache is invalidated, it is not needed at the time but some
        # code might one day go through _get_host_id_from_domain
        # before reaching this code, making this test useless
        self.env.transaction.invalidate_ormcache()
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
