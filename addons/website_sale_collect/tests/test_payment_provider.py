# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestOnSitePaymentProvider(HttpCase, ClickAndCollectCommon):

    def test_on_site_provider_available_when_in_store_delivery_is_chosen(self):
        order = self._create_in_store_delivery_order()
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(any(
            p.code == 'custom' and p.custom_mode == 'on_site' for p in compatible_providers
        ))

    def test_on_site_provider_unavailable_when_no_in_store_delivery(self):
        order = self._create_in_store_delivery_order(carrier_id=self.free_delivery.id)
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertFalse(any(
            p.code == 'custom' and p.custom_mode == 'on_site' for p in compatible_providers
        ))
