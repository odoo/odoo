# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


class CashOnDeliveryCommon(PaymentCustomCommon, DeliveryCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'state': 'draft',
        })
        cls.cod_provider = cls._prepare_provider(code='custom', custom_mode='cash_on_delivery')
