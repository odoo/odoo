# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
from uuid import uuid4

from odoo.addons.payment import utils as payment_utils

import requests

_logger = logging.getLogger(__name__)


class AuthorizeAPI:
    """ Authorize.net Gateway API integration.

    This class allows contacting the Authorize.net API with simple operation
    requests. It implements a *very limited* subset of the complete API
    (http://developer.authorize.net/api/reference); namely:
        - Customer Profile/Payment Profile creation
        - Transaction authorization/capture/voiding
    """

    AUTH_ERROR_STATUS = '3'

    def __init__(self, acquirer):
        """Initiate the environment with the acquirer data.

        :param recordset acquirer: payment.acquirer account that will be contacted
        """
        if acquirer.state == 'enabled':
            self.url = 'https://api.authorize.net/xml/v1/request.api'
        else:
            self.url = 'https://apitest.authorize.net/xml/v1/request.api'

        self.state = acquirer.state
        self.name = acquirer.authorize_login
        self.transaction_key = acquirer.authorize_transaction_key
        self.payment_method_type = acquirer.authorize_payment_method_type

    def _make_request(self, operation, data=None):
        request = {
            operation: {
                'merchantAuthentication': {
                    'name': self.name,
                    'transactionKey': self.transaction_key,
                },
                **(data or {})
            }
        }

        _logger.info("sending request to %s:\n%s", self.url, pprint.pformat(request))
        response = requests.post(self.url, json.dumps(request), timeout=60)
        response.raise_for_status()
        response = json.loads(response.content)
        _logger.info("response received:\n%s", pprint.pformat(response))

        messages = response.get('messages')
        if messages and messages.get('resultCode') == 'Error':
            err_msg = messages.get('message')[0]['text']

            tx_errors = response.get('transactionResponse', {}).get('errors')
            if tx_errors:
                if err_msg:
                    err_msg += '\n'
                err_msg += '\n'.join([e.get('errorText', '') for e in tx_errors])

            return {
                'err_code': messages.get('message')[0].get('code'),
                'err_msg': err_msg,
            }

        return response

    def _format_response(self, response, operation):
        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }
        else:
            return {
                'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
                'x_trans_id': response.get('transactionResponse', {}).get('transId'),
                'x_type': operation,
            }

    # Customer profiles
    def create_customer_profile(self, partner, transaction_id):
        """ Create an Auth.net payment/customer profile from an existing transaction.

        Creates a customer profile for the partner/credit card combination and links
        a corresponding payment profile to it. Note that a single partner in the Odoo
        database can have multiple customer profiles in Authorize.net (i.e. a customer
        profile is created for every res.partner/payment.token couple).

        Note that this function makes 2 calls to the authorize api, since we need to
        obtain a partial card number to generate a meaningful payment.token name.

        :param record partner: the res.partner record of the customer
        :param str transaction_id: id of the authorized transaction in the
                                   Authorize.net backend

        :return: a dict containing the profile_id and payment_profile_id of the
                 newly created customer profile and payment profile as well as the
                 last digits of the card number
        :rtype: dict
        """
        response = self._make_request('createCustomerProfileFromTransactionRequest', {
            'transId': transaction_id,
            'customer': {
                'merchantCustomerId': ('ODOO-%s-%s' % (partner.id, uuid4().hex[:8]))[:20],
                'email': partner.email or ''
            }
        })

        if not response.get('customerProfileId'):
            _logger.warning(
                "unable to create customer payment profile, data missing from transaction with "
                "id %(tx_id)s, partner id: %(partner_id)s",
                {
                    'tx_id': transaction_id,
                    'partner_id': partner,
                },
            )
            return False

        res = {
            'profile_id': response.get('customerProfileId'),
            'payment_profile_id': response.get('customerPaymentProfileIdList')[0]
        }

        response = self._make_request('getCustomerPaymentProfileRequest', {
            'customerProfileId': res['profile_id'],
            'customerPaymentProfileId': res['payment_profile_id'],
        })

        payment = response.get('paymentProfile', {}).get('payment', {})
        if self.payment_method_type == 'credit_card':
            res['name'] = payment.get('creditCard', {}).get('cardNumber')
        else:
            res['name'] = payment.get('bankAccount', {}).get('accountNumber')
        return res

    def delete_customer_profile(self, profile_id):
        """Delete a customer profile

        :param str profile_id: the id of the customer profile in the Authorize.net backend

        :return: a dict containing the response code
        :rtype: dict
        """
        response = self._make_request("deleteCustomerProfileRequest", {'customerProfileId': profile_id})
        return self._format_response(response, 'deleteCustomerProfile')

    #=== Transaction management ===#
    def _prepare_authorization_transaction_request(self, transaction_type, tx_data, tx):
        # The billTo parameter is required for new ACH transactions (transactions without a payment.token),
        # but is not allowed for transactions with a payment.token.
        bill_to = {}
        if 'profile' not in tx_data:
            split_name = payment_utils.split_partner_name(tx.partner_name)
            # max lengths are defined by the Authorize API
            bill_to = {
                'billTo': {
                    'firstName': '' if tx.partner_id.is_company else split_name[0][:50],
                    'lastName': split_name[1][:50],  # lastName is always required
                    'company': tx.partner_name[:50] if tx.partner_id.is_company else '',
                    'address': tx.partner_address,
                    'city': tx.partner_city,
                    'state': tx.partner_state_id.name or '',
                    'zip': tx.partner_zip,
                    'country': tx.partner_country_id.name or '',
                }
            }

        # These keys have to be in the order defined in
        # https://apitest.authorize.net/xml/v1/schema/AnetApiSchema.xsd
        return {
            'transactionRequest': {
                'transactionType': transaction_type,
                'amount': str(tx.amount),
                **tx_data,
                'order': {
                    'invoiceNumber': tx.reference[:20],
                    'description': tx.reference[:255],
                },
                'customer': {
                    'email': tx.partner_email or '',
                },
                **bill_to,
                'customerIP': payment_utils.get_customer_ip_address(),
            }
        }

    def authorize(self, tx, token=None, opaque_data=None):
        """ Authorize (without capture) a payment for the given amount.

        :param recordset tx: The transaction of the payment, as a `payment.transaction` record
        :param recordset token: The token of the payment method to charge, as a `payment.token`
                                record
        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        tx_data = self._prepare_tx_data(token=token, opaque_data=opaque_data)
        response = self._make_request(
            'createTransactionRequest',
            self._prepare_authorization_transaction_request('authOnlyTransaction', tx_data, tx)
        )
        return self._format_response(response, 'auth_only')

    def auth_and_capture(self, tx, token=None, opaque_data=None):
        """Authorize and capture a payment for the given amount.

        Authorize and immediately capture a payment for the given payment.token
        record for the specified amount with reference as communication.

        :param recordset tx: The transaction of the payment, as a `payment.transaction` record
        :param record token: the payment.token record that must be charged
        :param str opaque_data: the transaction opaque_data obtained from Authorize.net

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        tx_data = self._prepare_tx_data(token=token, opaque_data=opaque_data)
        response = self._make_request(
            'createTransactionRequest',
            self._prepare_authorization_transaction_request('authCaptureTransaction', tx_data, tx)
        )

        result = self._format_response(response, 'auth_capture')
        errors = response.get('transactionResponse', {}).get('errors')
        if errors:
            result['x_response_reason_text'] = '\n'.join([e.get('errorText') for e in errors])
        return result

    def _prepare_tx_data(self, token=None, opaque_data=False):
        """
        :param token: The token of the payment method to charge, as a `payment.token` record
        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        """
        assert (token or opaque_data) and not (token and opaque_data), "Exactly one of token or opaque_data must be specified"
        if token:
            token.ensure_one()
            return {
                'profile': {
                    'customerProfileId': token.authorize_profile,
                    'paymentProfile': {
                        'paymentProfileId': token.acquirer_ref,
                    }
                },
            }
        else:
            return {
                'payment': {
                    'opaqueData': opaque_data,
                }
            }

    def _get_transaction_details(self, transaction_id):
        """ Return detailed information about a specific transaction. Useful to issue refunds.

        :param str transaction_id: transaction id
        :return: a dict containing the transaction details
        :rtype: dict
        """
        return self._make_request('getTransactionDetailsRequest', {'transId': transaction_id})

    def capture(self, transaction_id, amount):
        """Capture a previously authorized payment for the given amount.

        Capture a previously authorized payment. Note that the amount is required
        even though we do not support partial capture.

        :param str transaction_id: id of the authorized transaction in the
                                   Authorize.net backend
        :param str amount: transaction amount (up to 15 digits with decimal point)

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        response = self._make_request('createTransactionRequest', {
            'transactionRequest': {
                'transactionType': 'priorAuthCaptureTransaction',
                'amount': str(amount),
                'refTransId': transaction_id,
            }
        })
        return self._format_response(response, 'prior_auth_capture')

    def void(self, transaction_id):
        """Void a previously authorized payment.

        :param str transaction_id: the id of the authorized transaction in the
                                   Authorize.net backend
        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        response = self._make_request('createTransactionRequest', {
            'transactionRequest': {
                'transactionType': 'voidTransaction',
                'refTransId': transaction_id
            }
        })
        return self._format_response(response, 'void')

    def refund(self, transaction_id, amount):
        """Refund a previously authorized payment. If the transaction is not settled
            yet, it will be voided.

        :param str transaction_id: the id of the authorized transaction in the
                                   Authorize.net backend
        :param float amount: transaction amount to refund
        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        tx_details = self._get_transaction_details(transaction_id)

        if tx_details and tx_details.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': tx_details.get('err_msg')
            }

        # Void transaction not yet settled instead of issuing a refund
        # (spoiler alert: a refund on a non settled transaction will throw an error)
        if tx_details.get('transaction', {}).get('transactionStatus') in ['authorizedPendingCapture', 'capturedPendingSettlement']:
            return self.void(transaction_id)

        card = tx_details.get('transaction', {}).get('payment', {}).get('creditCard', {}).get('cardNumber')
        response = self._make_request('createTransactionRequest', {
            'transactionRequest': {
                'transactionType': 'refundTransaction',
                'amount': str(amount),
                'payment': {
                    'creditCard': {
                        'cardNumber': card,
                        'expirationDate': 'XXXX',
                    }
                },
                'refTransId': transaction_id,
            }
        })
        return self._format_response(response, 'refund')

    # Acquirer configuration: fetch authorize_client_key & currencies
    def merchant_details(self):
        """ Retrieves the merchant details and generate a new public client key if none exists.

        :return: Dictionary containing the merchant details
        :rtype: dict"""
        return self._make_request('getMerchantDetailsRequest')

    # Test
    def test_authenticate(self):
        """ Test Authorize.net communication with a simple credentials check.

        :return: The authentication results
        :rtype: dict
        """
        return self._make_request('authenticateTestRequest')
