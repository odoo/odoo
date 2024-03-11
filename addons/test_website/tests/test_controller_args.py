# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteControllerArgs(odoo.tests.HttpCase):

    @mute_logger('odoo.http')
    def test_crawl_args(self):
        req = self.url_open('/ignore_args/converter/valueA/?b=valueB&c=valueC')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': 'valueA', 'b': 'valueB', 'kw': {'c': 'valueC'}})

        req = self.url_open('/ignore_args/converter/valueA/nokw?b=valueB&c=valueC')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': 'valueA', 'b': 'valueB'})

        req = self.url_open('/ignore_args/converteronly/valueA/?b=valueB&c=valueC')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': 'valueA', 'kw': None})

        req = self.url_open('/ignore_args/none?a=valueA&b=valueB')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': None, 'kw': None})

        req = self.url_open('/ignore_args/a?a=valueA&b=valueB')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': 'valueA', 'kw': None})

        req = self.url_open('/ignore_args/kw?a=valueA&b=valueB')
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json(), {'a': 'valueA', 'kw': {'b': 'valueB'}})

        req = self.url_open('/test_website/country/whatever-999999')
        self.assertEqual(req.status_code, 404,
                         "Model converter record does not exist, return a 404.")


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteControllers(odoo.tests.TransactionCase):

    def test_01_sitemap(self):
        website = self.env['website'].browse(1)
        locs = website.with_user(website.user_id)._enumerate_pages(query_string='test_website_sitemap')
        self.assertEqual(len(list(locs)), 1, "The same URL should only be shown once")
