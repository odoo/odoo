# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class BictorysCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bictorys = cls._prepare_provider('bictorys', update_values={
            'bictorys_secret_key': 'dummy_secret_key',
            'bictorys_webhook_secret': 'dummy_webhook_secret',
        })

        # Override default values.
        cls.provider = cls.bictorys
        cls.currency = cls.env.ref('base.XOF')

        cls.notification_data = {
            'paymentReference': cls.reference,
            'status': 'successful',
            'id': 'bictorys_tx_123',
            'amount': str(cls.amount),
            'currency': cls.currency.name,
        }
