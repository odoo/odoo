# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.website_sale_collect.tests.common import OnSiteCommon


@tagged('post_install', '-at_install')
class TestOnSitePayment(HttpCase, OnSiteCommon):

    def test_on_site_provider_available_when_in_store_delivery_is_chosen(self):
        order = self._create_so()
        order.carrier_id = self.carrier.id
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(any(
            p.code == 'custom' and p.custom_mode == 'on_site' for p in compatible_providers
        ))

    def test_on_site_provider_unavailable_when_no_in_store_delivery(self):
        order = self._create_so()
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(not any(
            p.code == 'custom' and p.custom_mode == 'on_site' for p in compatible_providers
        ))

    def test_choosing_on_site_payment_confirms_order(self):
        order = self._create_so(carrier_id=self.carrier.id, state='draft')
        tx = self._create_transaction(
            flow='direct',
            sale_order_ids=[order.id],
            state='pending',
            payment_method_id=self.provider.payment_method_ids.id,
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(order.state, 'sale')
