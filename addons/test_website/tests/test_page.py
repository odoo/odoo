# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install')
class WithContext(HttpCase):
    def test_01_homepage_url(self):
        # Setup
        website = self.env['website'].browse([1])
        website.write({
            'name': 'Test Website',
            'domain': self.base_url(),
            'homepage_url': '/unexisting',
        })
        home_url = '/'
        contactus_url = '/contactus'
        contactus_url_full = website.domain + contactus_url
        contactus_content = b'content="Contact Us | Test Website"'
        self.env['website.menu'].search([
            ('website_id', '=', website.id),
            ('url', '=', contactus_url),
        ]).sequence = 1

        # 404 shouldn't be served but fallback on first menu
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #    yes        | /contactus  |  /unexisting
        # -------------------------------------------
        r = self.url_open(website.homepage_url)
        self.assertEqual(r.status_code, 404, "The website homepage_url should be a 404")
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertURLEqual(r.url, contactus_url_full)
        self.assertIn(contactus_content, r.content)

        # same with 403
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #    yes        | /contactus  |  /test_website/200/name-1
        # -------------------------------------------
        rec_unpublished = self.env['test.model'].create({
            'name': 'name',
            'is_published': False,
        })
        website.homepage_url = f"/test_website/200/name-{rec_unpublished.id}"
        with mute_logger('odoo.http'):  # mute 403 warning
            r = self.url_open(website.homepage_url)
        self.assertEqual(r.status_code, 404, "The website homepage_url should be a 404")
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertURLEqual(r.url, contactus_url_full)
        self.assertIn(contactus_content, r.content)
