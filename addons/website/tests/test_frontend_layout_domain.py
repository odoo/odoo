# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests import HttpCase, new_test_user, tagged


@tagged('-at_install', 'post_install')
class TestFrontendLayoutDomain(HttpCase):
    """ The frontend chrome is decided by the domain used to reach Odoo.

    When the requested domain matches a website, that website's layout is
    rendered, no matter which company owns the visited document. When it
    matches none and no website acts as a catch-all (i.e. every website has a
    domain), no website is resolved at all and the frontend behaves as if the
    website module were not installed: portal pages keep the plain portal
    layout and website-only URLs are not served.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_2 = cls.env['res.company'].create({'name': 'Company 2'})

        # Bind every website to a domain that is never the one the tests are
        # served on, so that the requested host matches no website and none
        # acts as a catch-all. Tests needing a website resolved point one at
        # `base_url()` (the host used by `url_open`) instead of overriding the
        # `Host` header: `requests` matches cookies against that header, so
        # overriding it would drop the session cookie and log the user out.
        cls.env['website'].search([]).domain = 'website-1.test'
        cls.website_1 = cls.env.ref('base.default_website')
        cls.website_2 = cls.env['website'].create({
            'name': 'Website 2',
            'domain': 'website-2.test',
            'company_id': cls.company_2.id,
        })

        # A portal user of company 1, used to browse company 2's website.
        cls.portal_user = new_test_user(
            cls.env,
            login='portal_layout',
            password='portal_layout',
            groups='base.group_portal',
        )

    def _open(self, url):
        res = self.url_open(url)
        return res, html.fromstring(res.content)

    def _website_id(self, tree):
        """ ``data-website-id`` is only set by ``website.layout``. """
        return tree.xpath('//html/@data-website-id')

    def _serve_website_2_on_test_host(self):
        """ Make the host used by the tests resolve to website 2. """
        self.website_2.domain = self.base_url()

    # -- No matching domain: no website chrome -------------------------------

    def test_unmatched_domain_portal_page_has_no_chrome(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res, tree = self._open('/my/home')

        self.assertEqual(res.status_code, 200)
        self.assertFalse(
            self._website_id(tree),
            "Without a website for the requested domain, the portal page must "
            "render on the plain portal layout.",
        )
        self.assertTrue(
            tree.xpath('//div[contains(@class, "o_portal_my_home")]'),
            "The portal content itself must still be rendered, got %r (%s)" % (
                (tree.xpath('//title/text()') or [''])[0].strip(), res.url,
            ),
        )

    def test_unmatched_domain_homepage_redirects_to_login(self):
        self.authenticate(None, None)
        res, tree = self._open('/')

        self.assertEqual(res.status_code, 200)
        self.assertIn(
            '/web/login', res.url,
            "Without a website for the requested domain, `/` must lead to the "
            "login page, as it does when the website module is not installed.",
        )
        self.assertFalse(self._website_id(tree))

    def test_unmatched_domain_website_page_is_not_served(self):
        self.authenticate(None, None)
        res, __ = self._open('/contactus')

        self.assertEqual(
            res.status_code, 404,
            "Website pages must not be served on a domain that matches no website.",
        )

    # -- Matching domain: website chrome, whatever the company ---------------

    def test_matched_domain_homepage_renders_website(self):
        self._serve_website_2_on_test_host()
        self.authenticate(None, None)
        res, tree = self._open('/')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._website_id(tree), [str(self.website_2.id)])

    def test_matched_domain_portal_page_has_chrome_cross_company(self):
        self._serve_website_2_on_test_host()
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res, tree = self._open('/my/home')

        self.assertEqual(res.status_code, 200)
        # Also assert the portal content: the login page is rendered with
        # `website.layout` too, so `data-website-id` alone would not prove the
        # portal page itself was served.
        self.assertTrue(
            tree.xpath('//div[contains(@class, "o_portal_my_home")]'),
            "The portal page must be served, got %r (%s)" % (
                (tree.xpath('//title/text()') or [''])[0].strip(), res.url,
            ),
        )
        self.assertEqual(
            self._website_id(tree), [str(self.website_2.id)],
            "The domain decides the chrome: a user of company 1 reaching "
            "company 2's website gets that website's layout.",
        )
