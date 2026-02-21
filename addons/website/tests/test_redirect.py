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
            self.assertNotIn('/test', urls)


@tagged('-at_install', 'post_install')
class TestConditionalRedirects(HttpCase):

    def setUp(self):
        super().setUp()
        # Create a test group for checking group-based access
        self.test_group = self.env['res.groups'].create({'name': 'Test Group'})
        group_portal = self.env.ref('base.group_portal').id
        # Prepare test user data:
        # - One user belonging to 'Test Group'
        # - One user does not belonging to 'Test Group'
        users_data = [
            ('test_user_in_group', [group_portal, self.test_group.id]),
            ('test_user_not_in_group', [group_portal]),
        ]
        self.users = {}
        for login, groups in users_data:
            self.users[login] = self.env['res.users'].with_context(no_reset_password=True).create({
                'name': login.replace('_', ' ').title(),
                'login': login,
                'password': login,
                'email': f"{login}@mail.com",
                'group_ids': [(6, 0, groups)],
            })
        self.env['website.page'].create([
        {
            'name': 'Original Page',
            'url': '/original-page',
            'is_published': False,
            'type': 'qweb',
            'arch': '<div>Original Page Content</div>',
        },
        {
            'name': 'Redirected Page',
            'url': '/redirected-page',
            'is_published': True,
            'type': 'qweb',
            'arch': '<div>Redirected Page Content</div>',
        }
        ])
        self.urls = {
            '301': {'from': '/original-page?redirect=301', 'to': '/redirected-page?redirect=301'},
            '302': {'from': '/original-page?redirect=302', 'to': '/redirected-page?redirect=302'},
            '404': {'from': '/website/info', 'to': None},
        }

    def _create_rewrite_rules(self, apply_to, redirect_types=('301', '302', '404')):
        """Helper to create a set of rewrite rules."""
        for r_type in redirect_types:
            vals = {
                'name': f'Test {apply_to} {r_type}',
                'redirect_type': r_type,
                'url_from': self.urls[r_type]['from'],
                'apply_to_group': apply_to,
            }
            if apply_to != 'all_users':
                vals['user_group_ids'] = [(6, 0, [self.test_group.id])]
            if self.urls[r_type]['to']:
                vals['url_to'] = self.urls[r_type]['to']
            self.env['website.rewrite'].create(vals)

    def _assert_redirect(self, url_from, expected_url, expected_status):
        """Helper: perform URL open and validate redirect or not."""
        resp = self.url_open(url_from)
        self.assertEqual(resp.status_code, expected_status)
        target = expected_url or url_from
        self.assertTrue(
            resp.url.endswith(target),
            f"Expected redirect target: {target}, got: {resp.url}",
        )

    def _test_redirect_behavior(self, user_login, expectations):
        """Helper: authenticate user and validate expected redirect behavior."""
        if user_login:
            self.authenticate(user_login, user_login)

        for r_type, (status, should_redirect) in expectations.items():
            exp_url = self.urls[r_type]['to'] if should_redirect else None
            self._assert_redirect(self.urls[r_type]['from'], exp_url, status)

    def test_01_all_users(self):
        """Test redirects applied to 'all_users'."""
        self._create_rewrite_rules('all_users')
        # Both users behave the same
        expectations = {
            '301': (200, True),
            '302': (200, True),
            '404': (404, False),
        }
        for user in self.users.values():
            self._test_redirect_behavior(user.login, expectations)

    def test_02_if_user_in_group(self):
        """Test redirects applied only if user 'in_group'."""
        self._create_rewrite_rules('in_group')
        # Public user: should not redirect
        public_expectations = {
            '301': (404, False),
            '302': (404, False),
        }
        self._test_redirect_behavior(None, public_expectations)
        # User in group: should redirect
        in_group_expectations = {
            '301': (200, True),
            '302': (200, True),
            '404': (404, False),
        }
        self._test_redirect_behavior('test_user_in_group', in_group_expectations)
        # User not in group: should not redirect
        not_in_group_expectations = {
            '301': (404, False),
            '302': (404, False),
            '404': (200, False),
        }
        self._test_redirect_behavior('test_user_not_in_group', not_in_group_expectations)

    def test_03_if_user_not_in_group(self):
        """Test redirects applied only if user is 'not_in_group'."""
        self._create_rewrite_rules('not_in_group')
        # Public user: should redirect
        public_expectations = {
            '301': (200, True),
            '302': (200, True),
        }
        self._test_redirect_behavior(None, public_expectations)
        # User in group: should not redirect
        in_group_expectations = {
            '301': (404, False),
            '302': (404, False),
            '404': (200, False),
        }
        self._test_redirect_behavior('test_user_in_group', in_group_expectations)
        # User not in group: should redirect
        not_in_group_expectations = {
            '301': (200, True),
            '302': (200, True),
            '404': (404, False),
        }
        self._test_redirect_behavior('test_user_not_in_group', not_in_group_expectations)
