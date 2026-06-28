# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged("post_install", "-at_install")
class TestCODPaymentProvider(CashOnDeliveryCommon):
    def test_cod_provider_available_when_dm_cod_enabled(self):
        order = self.sale_order
        self.free_delivery.allow_cash_on_delivery = True
        order.carrier_id = self.free_delivery
        available_providers = (
            self
            .env["payment.provider"]
            .sudo()
            ._find_available_providers(
                self.company.id, self.partner.id, self.amount, sale_order_id=order.id
            )
        )
        self.assertTrue(
            any(
                p.code == "custom" and p.custom_mode == "cash_on_delivery"
                for p in available_providers
            )
        )

    def test_cod_provider_unavailable_when_dm_cod_disabled(self):
        order = self.sale_order
        self.free_delivery.allow_cash_on_delivery = False
        order.carrier_id = self.free_delivery
        available_providers = (
            self
            .env["payment.provider"]
            .sudo()
            ._find_available_providers(
                self.company.id, self.partner.id, self.amount, sale_order_id=order.id
            )
        )
        self.assertFalse(
            any(
                p.code == "custom" and p.custom_mode == "cash_on_delivery"
                for p in available_providers
            )
        )
