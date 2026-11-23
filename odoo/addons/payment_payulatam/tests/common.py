# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class PayULatamCommon(AccountTestInvoicingCommon, PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payulatam = cls._prepare_provider('payulatam', update_values={
            'payulatam_account_id': 'dummy',
            'payulatam_merchant_id': 'dummy',
            'payulatam_api_key': 'dummy',
        })

        # Override default values
        cls.provider = cls.payulatam
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

        cls.async_notification_data_webhook = cls.async_notification_data.copy()
        cls.async_notification_data_webhook["sign"] = 'e227f90e64808320953dbbcb5ee96c9f'
