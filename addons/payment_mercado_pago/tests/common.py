# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class MercadoPagoCommon(PaymentCommon):

    MP_PAYMENT_ID = '1234567890'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.provider = cls._prepare_provider('mercado_pago', update_values={
            'mercado_pago_access_token': 'TEST-4850554046279901-TEST-TEST',
        })
        cls.payment_id = '123456'
        cls.redirect_notification_data = {
            'external_reference': cls.reference,
            'payment_id': cls.payment_id,
        }
        cls.webhook_notification_data = {
            'action': 'payment.created',
            'data': {'id': cls.payment_id},
        }
        cls.verification_data = {
            'status': 'approved',
        }
        cls.verification_data_for_error_state = {
            'status': 404,
        }
