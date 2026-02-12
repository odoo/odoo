# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon
from odoo.addons.sale.tests.common import SaleCommon


class CashOnDeliveryCommon(PaymentCustomCommon, SaleCommon, DeliveryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.free_delivery.allow_cash_on_delivery = True
        (cls.empty_order + cls.sale_order).set_delivery_line(cls.free_delivery, 0)
        cls.cod_provider = cls._prepare_provider(code='custom', custom_mode='cash_on_delivery')

    @classmethod
    def _create_cod_transaction(cls, sale_order=None, **values):
        sale_order = (sale_order or cls.sale_order).ensure_one()
        return cls._create_transaction(
            flow='direct',
            sale_order_ids=[Command.set(sale_order.ids)],
            partner_id=sale_order.partner_id.id,
            amount=sale_order.amount_total,
            currency_id=sale_order.currency_id.id,
            state='pending',
            provider_id=cls.cod_provider.id,
            payment_method_id=cls.cod_provider.payment_method_ids.id,
            reference=False,  # Force the computation of an unique reference
            **values,
        )

    def assert_dict_almost_equal(self, d1, d2, msg=None):
        self.assertIsInstance(d1, dict, msg=msg)
        self.assertIsInstance(d2, dict, msg=msg)
        self.assertDictEqual({key: d1[key] for key in d1.keys() & d2.keys()}, d2, msg=msg)
