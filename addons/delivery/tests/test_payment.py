# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


@tagged('post_install', '-at_install')
class TestCODPayment(PaymentCustomCommon, DeliveryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'state': 'draft',
        })
        cls.cod_provider = cls._prepare_provider('cash_on_delivery')

    def test_cod_provider_available_when_dm_cod_enabled(self):
        order = self.sale_order
        self.free_delivery.is_cash_on_delivery_enabled = True
        order.carrier_id = self.free_delivery
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(any(
            p.code == 'custom' and p.custom_mode == 'cash_on_delivery' for p in compatible_providers
        ))

    def test_cod_provider_unavailable_when_dm_cod_disabled(self):
        order = self.sale_order
        self.free_delivery.is_cash_on_delivery_enabled = False
        order.carrier_id = self.free_delivery
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(not any(
            p.code == 'custom' and p.custom_mode == 'cash_on_delivery' for p in compatible_providers
        ))

    def test_choosing_cod_payment_confirms_order(self):
        order = self.sale_order
        self.free_delivery.is_cash_on_delivery_enabled = True
        order.carrier_id = self.free_delivery
        tx = self._create_transaction(
            flow='direct',
            sale_order_ids=[order.id],
            state='pending',
            provider_id=self.cod_provider.id,
            payment_method_id=self.cod_provider.payment_method_ids.id,
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(order.state, 'sale')
