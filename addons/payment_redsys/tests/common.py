# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo.addons.payment.tests.common import PaymentCommon


class RedsysCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.redsys = cls._prepare_provider('redsys', update_values={
            'redsys_merchant_code': '99999999',
            'redsys_merchant_terminal': '777',
            'redsys_secret_key': 'a1b2c3d4e5f6g7h8a1b2c3d4e5f6g7h8',
        })
        cls.provider = cls.redsys
        cls.merchant_parameters = {
            'Ds_Order': 'Test Transaction',
            'Ds_Amount': cls.amount * 100,  # In minor units
            'Ds_Currency': 978,  # EUR
            'Ds_Card_Brand': '1',  # VISA
            'Ds_Response': '0000',  # Payment accepted
        }
        cls.encoded_merchant_parameter = base64.b64encode(
            json.dumps(cls.merchant_parameters).encode()
        ).decode()
        cls.payment_data = {
            'Ds_MerchantParameters': cls.encoded_merchant_parameter,
            'Ds_Signature': 'upzUj96lLgOEUP5lvaj7lz0Se4MXmc5_GoJ32ACqZ3A=',
        }
