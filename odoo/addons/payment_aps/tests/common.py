# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.http_common import PaymentHttpCommon


class APSCommon(PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.aps = cls._prepare_provider('aps', update_values={
            'aps_merchant_identifier': '123456abc',
            'aps_access_code': 'dummy',
            'aps_sha_request': 'dummy',
            'aps_sha_response': 'dummy',
        })

        cls.provider = cls.aps

        cls.notification_data = {
            'access_code': cls.provider.aps_access_code,
            'amount': cls.amount,
            'authorization_code': '123456',
            'card_holder_name': 'Mitchell',
            'card_number': '************1111',
            'command': 'PURCHASE',
            'currency': 'USD',
            'customer_email': '	admin@yourcompany.example.com',
            'customer_ip': '123.456.78.90',
            'eci': 'ECOMMERCE',
            'expiry_date': '2212',
            'fort_id': '169996210006464984',
            'language': 'en',
            'merchant_identifier': cls.provider.aps_merchant_identifier,
            'merchant_reference': cls.reference,
            'payment_option': 'VISA',
            'response_code': '14000',
            'response_message': 'Success',
            'signature': '6d2bb7904ac6141a0c10375c70fd417616c740bb1ddab862a224777880aa3600',
            'status': '14',
            'token_name': '123abc456def789',
        }
