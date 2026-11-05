# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase


class TestDisableModule(HttpCase):
    """Per-website module disabling: a feature turned off on one website must
    404 its public routes there while staying available on the others, without
    touching the module's data."""

    def test_blog_disabled_per_website(self):
        default_website = self.env.ref('base.default_website')
        default_website.domain = False
        other_website = self.env['website'].create({
            'name': 'Other Website',
            'domain': 'website-other.test',
        })

        blog = self.env['blog.blog'].create({'name': 'Test Blog'})

        headers_other = {'Host': 'website-other.test'}

        # baseline: /blog is a public page (200) on both websites
        self.assertEqual(self.url_open('/blog').status_code, 200)
        self.assertEqual(self.url_open('/blog', headers=headers_other).status_code, 200)

        # disable the blog feature on the default website only
        blog_module = self.env['ir.module.module']._get('website_blog')
        default_website.disabled_module_ids = [Command.link(blog_module.id)]

        # public visitor: 404 on the default website, still 200 on the other one
        self.assertEqual(self.url_open('/blog').status_code, 404)
        self.assertEqual(self.url_open('/blog', headers=headers_other).status_code, 200)

        # a designer (admin) can still reach the page
        self.authenticate('admin', 'admin')
        self.assertEqual(self.url_open('/blog').status_code, 200)
        self.authenticate(None, None)  # back to a public session

        # re-enabling restores public access (data was never removed)
        default_website.disabled_module_ids = [Command.unlink(blog_module.id)]
        self.assertEqual(self.url_open(f'/blog/{blog.id}').status_code, 200)

    def test_disableable_modules_eligibility(self):
        """Only installed website feature modules are disable-eligible; infra
        modules are excluded by the data-driven domain."""
        Module = self.env['ir.module.module']
        domain = self.env['website']._get_disableable_modules_domain()
        eligible = Module.search(domain).mapped('name')
        self.assertIn('website_blog', eligible)
        for module in ('base', 'web', 'http_routing', 'portal', 'website'):
            self.assertNotIn(module, eligible, f"{module} must never be disable-eligible")
