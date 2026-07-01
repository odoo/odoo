# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestOnSitePaymentProvider(HttpCase, ClickAndCollectCommon):
    def test_on_site_provider_available_when_in_store_delivery_is_chosen(self):
        order = self._create_in_store_delivery_order()
        PaymentProvider = self.env["payment.provider"].sudo()
        available_providers = PaymentProvider._find_available_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(
            any(p.code == "custom" and p.custom_mode == "on_site" for p in available_providers)
        )

    def test_on_site_provider_unavailable_when_no_in_store_delivery(self):
        order = self._create_in_store_delivery_order(carrier_id=self.free_delivery.id)
        PaymentProvider = self.env["payment.provider"].sudo()
        available_providers = PaymentProvider._find_available_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertFalse(
            any(p.code == "custom" and p.custom_mode == "on_site" for p in available_providers)
        )

    def test_on_site_provider_unavailable_if_amount_is_less_than_remaining_balance(self):
        order = self._create_in_store_delivery_order()
        prepaid_amount = self.sale_order.currency_id.round(self.sale_order.amount_total / 3)
        self._create_transaction(
            flow="direct",
            sale_order_ids=[Command.set(order.ids)],
            partner_id=order.partner_id.id,
            amount=prepaid_amount,
            currency_id=order.currency_id.id,
            state="done",
        )
        self.assertEqual(order.amount_paid, prepaid_amount)

        # Try to pay again for the second third of the total order amount
        available_providers = (
            self
            .env["payment.provider"]
            .sudo()
            ._find_available_providers(
                self.company.id, self.partner.id, order.amount_total / 3, sale_order_id=order.id
            )
        )

        self.assertFalse(
            any(
                p.code == "custom" and p.custom_mode == "cash_on_delivery"
                for p in available_providers
            )
        )
