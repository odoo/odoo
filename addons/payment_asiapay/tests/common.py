# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.payment.tests.common import PaymentCommon


class AsiaPayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.asiapay = cls._prepare_provider('asiapay', update_values={
            'asiapay_merchant_id': '123456789',
            'asiapay_secure_hash_secret': 'coincoin_motherducker',
            'asiapay_secure_hash_function': 'sha1',
            'available_currency_ids': [Command.set(cls.currency_euro.ids)],
        })

        cls.provider = cls.asiapay

        cls.redirect_notification_data = {
            'Ref': cls.reference,
        }
        cls.webhook_notification_data = {
            'src': 'dummy',
            'prc': 'dummy',
            'successcode': '0',
            'Ref': cls.reference,
            'PayRef': 'dummy',
            'Cur': cls.currency.name,
            'Amt': cls.amount,
            'payerAuth': 'dummy',
            'secureHash': '3e5bf55d9a23969130a6686db7aa4f0230956d0a',
        }
