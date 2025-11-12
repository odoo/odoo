# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged("post_install", "-at_install")
class TestCODPaymentProvider(CashOnDeliveryCommon):
    def test_cod_provider_available_when_dm_cod_enabled(self):
        order = self.sale_order
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

    def test_cod_provider_unavailable_if_amount_is_less_than_remaining_balance(self):
        order = self.sale_order
        prepaid_amount = order.currency_id.round(order.amount_total / 3)
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
