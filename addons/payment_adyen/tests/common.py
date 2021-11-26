# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

from odoo.tools import mute_logger


class AdyenCommon(PaymentCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.adyen = cls._prepare_acquirer('adyen', update_values={
            'adyen_merchant_account': 'dummy',
            'adyen_api_key': 'dummy',
            'adyen_client_key': 'dummy',
            'adyen_hmac_key': '12345678',
            'adyen_checkout_api_url': 'https://this.is.an.url',
            'adyen_recurring_api_url': 'https://this.is.an.url',
        })

        # Override default values
        cls.acquirer = cls.adyen

    def create_payload(self, received_signature):
        """ Create a dummy payload.

        :param str received_signature: the HMAC signature
        :return: The payload created by the payment flow
        :rtype:  dict
        """

        # Create a dummy invoice
        account = self.env['account.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2021-11-23',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_euro.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_euro.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })

        # Create transaction
        route_values = self._prepare_pay_values()
        route_values['invoice_id'] = invoice.id
        tx_context = self.get_tx_checkout_context(**route_values)

        route_values = {
            k: tx_context[k]
            for k in [
                'amount',
                'currency_id',
                'reference_prefix',
                'partner_id',
                'access_token',
                'landing_route',
                'invoice_id',
            ]
        }

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
        })

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        # Create payload
        payload = {
            'notificationItems': [
                {'NotificationRequestItem':
                    {
                        'additionalData': {
                            'hmacSignature': received_signature,
                        },
                        'merchantReference': tx_sudo.reference,
                        'success': '',
                        'eventCode': ''
                    }
                }
            ]
        }

        return payload
