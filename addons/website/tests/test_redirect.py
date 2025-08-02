# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteRedirect(TransactionCase):
    def test_01_website_redirect_validation(self):
        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/',
            })
        self.assertIn('homepage', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico',
            })
        self.assertIn('existing page', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico/',  # trailing slash on purpose
            })
        self.assertIn('existing page', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '301',
                'url_from': '/website/info',
                'url_to': '#',
            })
        self.assertIn("must not start with '#'", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '301',
                'url_from': '/website/info',
                'url_to': '/website/info',
            })
        self.assertIn("should not be same", str(error.exception))

    def test_sitemap_with_redirect(self):
        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/website/info',
            'url_to': '/test',
        })
        website = self.env.ref('website.default_website')
        with MockRequest(self.env, website=website):
            self.env['website.rewrite'].refresh_routes()
            pages = self.env.ref('website.default_website')._enumerate_pages()
            urls = [url['loc'] for url in pages]
            self.assertIn('/website/info', urls)
            self.assertNotIn('/test', urls)


@tagged('-at_install', 'post_install')
class TestConditionalRedirects(HttpCase):

    def setUp(self):
        super().setUp()
        self.test_group = self.env['res.groups'].create({'name': 'Test Group'})
        # User who is a member of the test group
        self.user_in_group = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Test User In Group',
            'login': 'test_user_in_group',
            'password': 'test_user_in_group',
            'email': 'test_user_in_group@mail.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id, self.test_group.id])]
        })
        # User who is NOT a member of the test group
        self.user_not_in_group = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Test User Not In Group',
            'login': 'test_user_not_in_group',
            'password': 'test_user_not_in_group',
            'email': 'test_user_not_in_group@mail.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.original_page = self.env['website.page'].create({
            'name': 'Original Page',
            'url': '/original-page',
            'is_published': False,
            'type': 'qweb',
            'arch': '<div>Original Page Content</div>',
        })
        self.redirected_page = self.env['website.page'].create({
            'name': 'Redirected Page',
            'url': '/redirected-page',
            'is_published': True,
            'type': 'qweb',
            'arch': '<div>Redirected Page Content</div>',
        })
        self.url_from_301 = '/original-page?redirect=301'
        self.url_to_301 = '/redirected-page?redirect=301'
        self.url_from_302 = '/original-page?redirect=302'
        self.url_to_302 = '/redirected-page?redirect=302'
        self.url_from_404 = '/website/info'

    def _create_rewrite_rules(self, apply_to, redirect_types=None):
        """Helper to create a set of rewrite rules for testing."""
        if redirect_types is None:
            redirect_types = ['301', '302', '404']
        for r_type in redirect_types:
            url_from = f"/original-page?redirect={r_type}" if r_type != '404' else self.url_from_404
            url_to = f"/redirected-page?redirect={r_type}" if r_type != '404' else None
            vals = {
                'name': f'Test {apply_to} {r_type}',
                'redirect_type': r_type,
                'url_from': url_from,
                'apply_to_group': apply_to,
                'user_group_ids': [(6, 0, [self.test_group.id])] if apply_to != 'all_users' else False,
            }
            if url_to:
                vals['url_to'] = url_to
            self.env['website.rewrite'].create(vals)

    def test_01_all_users(self):
        """Test redirects applied to 'all_users'."""
        self._create_rewrite_rules('all_users')

        # Test as User IN group (should redirect/404)
        self.authenticate('test_user_in_group', 'test_user_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 200)
        self.assertTrue(r_301.url.endswith(self.url_to_301), "Ensure URL should have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 200)
        self.assertTrue(r_302.url.endswith(self.url_to_302), "Ensure URL should have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 404)

        # Test as User NOT in group (should redirect/404)
        self.authenticate('test_user_not_in_group', 'test_user_not_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 200)
        self.assertTrue(r_301.url.endswith(self.url_to_301), "Ensure URL should have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 200)
        self.assertTrue(r_302.url.endswith(self.url_to_302), "Ensure URL should have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 404)

    def test_02_if_has_group(self):
        """Test redirects applied only if user 'has_group'."""
        self._create_rewrite_rules('has_group')
        # Test as public user
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 404)
        self.assertTrue(r_301.url.endswith(self.url_from_301), "Ensure URL should not have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 404)
        self.assertTrue(r_302.url.endswith(self.url_from_302), "Ensure URL should not have been redirected")

        # Test as User IN group (should redirect/404)
        self.authenticate('test_user_in_group', 'test_user_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 200)
        self.assertTrue(r_301.url.endswith(self.url_to_301), "Ensure URL should have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 200)
        self.assertTrue(r_302.url.endswith(self.url_to_302), "Ensure URL should have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 404)

        # Test as User NOT in group (should NOT redirect/404)
        self.authenticate('test_user_not_in_group', 'test_user_not_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 404)
        self.assertTrue(r_301.url.endswith(self.url_from_301), "Ensure URL should not have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 404)
        self.assertTrue(r_302.url.endswith(self.url_from_302), "Ensure URL should not have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 200)

    def test_03_if_not_in_group(self):
        """Test redirects applied only if user is 'not_in_group'."""
        self._create_rewrite_rules('not_in_group')
        # Test as public user
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 200)
        self.assertTrue(r_301.url.endswith(self.url_to_301), "Ensure URL should have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 200)
        self.assertTrue(r_302.url.endswith(self.url_to_302), "Ensure URL should have been redirected")

        # Test as User IN group (should NOT redirect/404)
        self.authenticate('test_user_in_group', 'test_user_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 404)
        self.assertTrue(r_301.url.endswith(self.url_from_301), "Ensure URL should not have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 404)
        self.assertTrue(r_302.url.endswith(self.url_from_302), "Ensure URL should not have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 200)

        # Test as User NOT in group (should redirect/404)
        self.authenticate('test_user_not_in_group', 'test_user_not_in_group')
        r_301 = self.url_open(self.url_from_301)
        self.assertEqual(r_301.status_code, 200)
        self.assertTrue(r_301.url.endswith(self.url_to_301), "Ensure URL should have been redirected")

        r_302 = self.url_open(self.url_from_302)
        self.assertEqual(r_302.status_code, 200)
        self.assertTrue(r_302.url.endswith(self.url_to_302), "Ensure URL should have been redirected")

        r_404 = self.url_open(self.url_from_404)
        self.assertEqual(r_404.status_code, 404)
