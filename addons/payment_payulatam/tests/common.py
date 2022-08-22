# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PayULatamCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payulatam = cls._prepare_acquirer('payulatam', update_values={
            'payulatam_account_id': 'dummy',
            'payulatam_merchant_id': 'dummy',
            'payulatam_api_key': 'dummy',
        })

        # Override default values
        cls.acquirer = cls.payulatam
        cls.currency = cls.currency_euro

        cls.async_notification_data = {
            'currency': cls.currency.name,
            'reference_sale': cls.reference,
            'response_message_pol': 'APPROVED',
            'sign': '6b4728ddb01317af58f92b8accdb4a42',
            'state_pol': '4',
            'transaction_id': '7008bc34-8258-4857-b866-7d4d7982bd73',
            'value': str(cls.amount)
        }
