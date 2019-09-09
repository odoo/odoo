# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteControllerArgs(odoo.tests.HttpCase):

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
