# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged

from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestPaymentProvider(TransactionCase):

    def test_base_url_in_cron(self):
        """ The url of the request is not used in cron jobs, as it might not be reachable. """
        provider = self.env['payment.provider'].search([], limit=1)
        with MockRequest(self.env, url_root='https://request.example.com/'):
            self.assertEqual(provider.get_base_url(), 'https://request.example.com/')
            self.assertNotIn('request.example.com', provider.with_context(cron_id=1).get_base_url())
