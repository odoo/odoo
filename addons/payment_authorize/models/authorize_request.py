# -*- coding: utf-8 -*-
import json
import logging
import requests

from uuid import uuid4

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.payment.models.payment_acquirer import _partner_split_name

_logger = logging.getLogger(__name__)


class AuthorizeAPI():
    """Authorize.net Gateway API integration.

    This class allows contacting the Authorize.net API with simple operation
    requests. It implements a *very limited* subset of the complete API
    (http://developer.authorize.net/api/reference); namely:
        - Customer Profile/Payment Profile creation
        - Transaction authorization/capture/voiding
    """

    AUTH_ERROR_STATUS = 3

    def __init__(self, acquirer):
        """Initiate the environment with the acquirer data.

        :param record acquirer: payment.acquirer account that will be contacted
        """
        if acquirer.state == 'test':
            self.url = 'https://apitest.authorize.net/xml/v1/request.api'
        else:
            self.url = 'https://api.authorize.net/xml/v1/request.api'

        self.state = acquirer.state
        self.name = acquirer.authorize_login
        self.transaction_key = acquirer.authorize_transaction_key

    def _authorize_request(self, data):
        _logger.info('_authorize_request: Sending values to URL %s, values:\n%s', self.url, data)
        resp = requests.post(self.url, json.dumps(data))
        resp.raise_for_status()
        resp = json.loads(resp.content)
        messages = resp.get('messages')
        if messages and messages.get('resultCode') == 'Error':
            return {
                'err_code': messages.get('message')[0].get('code'),
                'err_msg': messages.get('message')[0].get('text')
            }

        return resp

    # Customer profiles
    def create_customer_profile(self, partner, opaqueData):
        """Create a payment and customer profile in the Authorize.net backend.

        Creates a customer profile for the partner/credit card combination and links
        a corresponding payment profile to it. Note that a single partner in the Odoo
        database can have multiple customer profiles in Authorize.net (i.e. a customer
        profile is created for every res.partner/payment.token couple).

        :param record partner: the res.partner record of the customer
        :param str cardnumber: cardnumber in string format (numbers only, no separator)
        :param str expiration_date: expiration date in 'YYYY-MM' string format
        :param str card_code: three- or four-digit verification number

        :return: a dict containing the profile_id and payment_profile_id of the
                 newly created customer profile and payment profile
        :rtype: dict
        """
        values = {
            'createCustomerProfileRequest': {
                'merchantAuthentication': {
                    'name': self.name,
                    'transactionKey': self.transaction_key
                },
                'profile': {
                    'description': ('ODOO-%s-%s' % (partner.id, uuid4().hex[:8]))[:20],
                    'email': partner.email or '',
                    'paymentProfiles': {
                        'customerType': 'business' if partner.is_company else 'individual',
                        'billTo': {
                            'firstName': '' if partner.is_company else _partner_split_name(partner.name)[0],
                            'lastName':  _partner_split_name(partner.name)[1],
                            'address': (partner.street or '' + (partner.street2 if partner.street2 else '')) or None,
                            'city': partner.city,
                            'state': partner.state_id.name or None,
                            'zip': partner.zip or '',
                            'country': partner.country_id.name or None
                        },
                        'payment': {
                            'opaqueData': {
                                'dataDescriptor': opaqueData.get('dataDescriptor'),
                                'dataValue': opaqueData.get('dataValue')
                            }
                        }
                    }
                },
                'validationMode': 'liveMode' if self.state == 'enabled' else 'testMode'
            }
        }

        response = self._authorize_request(values)

        if response and response.get('err_code'):
            raise UserError(_(
                "Authorize.net Error:\nCode: %s\nMessage: %s"
                % (response.get('err_code'), response.get('err_msg'))
            ))

        return {
            'profile_id': response.get('customerProfileId'),
            'payment_profile_id': response.get('customerPaymentProfileIdList')[0]
        }

    def create_customer_profile_from_tx(self, partner, transaction_id):
        """Create an Auth.net payment/customer profile from an existing transaction.

        Creates a customer profile for the partner/credit card combination and links
        a corresponding payment profile to it. Note that a single partner in the Odoo
        database can have multiple customer profiles in Authorize.net (i.e. a customer
        profile is created for every res.partner/payment.token couple).

        Note that this function makes 2 calls to the authorize api, since we need to
        obtain a partial cardnumber to generate a meaningful payment.token name.

        :param record partner: the res.partner record of the customer
        :param str transaction_id: id of the authorized transaction in the
                                   Authorize.net backend

        :return: a dict containing the profile_id and payment_profile_id of the
                 newly created customer profile and payment profile as well as the
                 last digits of the card number
        :rtype: dict
        """
        values = {
            'createCustomerProfileFromTransactionRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'transId': transaction_id,
                'customer': {
                    'merchantCustomerId': ('ODOO-%s-%s' % (partner.id, uuid4().hex[:8]))[:20],
                    'email': partner.email or ''
                }
            }
        }

        response = self._authorize_request(values)

        if not response.get('customerProfileId'):
            _logger.warning(
                'Unable to create customer payment profile, data missing from transaction. Transaction_id: %s - Partner_id: %s'
                % (transaction_id, partner)
            )
            return False

        res = {
            'profile_id': response.get('customerProfileId'),
            'payment_profile_id': response.get('customerPaymentProfileIdList')[0]
        }

        values = {
            'getCustomerPaymentProfileRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'customerProfileId': res['profile_id'],
                'customerPaymentProfileId': res['payment_profile_id'],
            }
        }

        response = self._authorize_request(values)

        res['name'] = response.get('paymentProfile', {}).get('payment', {}).get('creditCard', {}).get('cardNumber')
        return res

    # Transaction management
    def auth_and_capture(self, token, amount, reference):
        """Authorize and capture a payment for the given amount.

        Authorize and immediately capture a payment for the given payment.token
        record for the specified amount with reference as communication.

        :param record token: the payment.token record that must be charged
        :param str amount: transaction amount (up to 15 digits with decimal point)
        :param str reference: used as "invoiceNumber" in the Authorize.net backend

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        values = {
            'createTransactionRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'transactionRequest': {
                    'transactionType': 'authCaptureTransaction',
                    'amount': str(amount),
                    'profile': {
                        'customerProfileId': token.authorize_profile,
                        'paymentProfile': {
                            'paymentProfileId': token.acquirer_ref,
                        }
                    },
                    'order': {
                        'invoiceNumber': reference[:20]
                    }
                }

            }
        }
        response = self._authorize_request(values)

        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }

        return {
            'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
            'x_trans_id': response.get('transactionResponse', {}).get('transId'),
            'x_type': 'auth_capture'
        }

    def authorize(self, token, amount, reference):
        """Authorize a payment for the given amount.

        Authorize (without capture) a payment for the given payment.token
        record for the specified amount with reference as communication.

        :param record token: the payment.token record that must be charged
        :param str amount: transaction amount (up to 15 digits with decimal point)
        :param str reference: used as "invoiceNumber" in the Authorize.net backend

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        values = {
            'createTransactionRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'transactionRequest': {
                    'transactionType': 'authOnlyTransaction',
                    'amount': str(amount),
                    'profile': {
                        'customerProfileId': token.authorize_profile,
                        'paymentProfile': {
                            'paymentProfileId': token.acquirer_ref,
                        }
                    },
                    'order': {
                        'invoiceNumber': reference[:20]
                    }
                }

            }
        }
        response = self._authorize_request(values)

        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }

        return {
            'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
            'x_trans_id': response.get('transactionResponse', {}).get('transId'),
            'x_type': 'auth_only'
        }

    def capture(self, transaction_id, amount):
        """Capture a previously authorized payment for the given amount.

        Capture a previsouly authorized payment. Note that the amount is required
        even though we do not support partial capture.

        :param str transaction_id: id of the authorized transaction in the
                                   Authorize.net backend
        :param str amount: transaction amount (up to 15 digits with decimal point)

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        values = {
            'createTransactionRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'transactionRequest': {
                    'transactionType': 'priorAuthCaptureTransaction',
                    'refTransId': transaction_id,
                    'amount': str(amount)
                }
            }
        }

        response = self._authorize_request(values)

        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }

        return {
            'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
            'x_trans_id': response.get('transactionResponse', {}).get('transId'),
            'x_type': 'prior_auth_capture'
        }

    def void(self, transaction_id):
        """Void a previously authorized payment.

        :param str transaction_id: the id of the authorized transaction in the
                                   Authorize.net backend

        :return: a dict containing the response code, transaction id and transaction type
        :rtype: dict
        """
        values = {
            'createTransactionRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
                'transactionRequest': {
                    'transactionType': 'voidTransaction',
                    'refTransId': transaction_id
                }
            }
        }

        response = self._authorize_request(values)

        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }

        return {
            'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
            'x_trans_id': response.get('transactionResponse', {}).get('transId'),
            'x_type': 'void'
        }

    # Test
    def test_authenticate(self):
        """Test Authorize.net communication with a simple credentials check.

        :return: True if authentication was successful, else False (or throws an error)
        :rtype: bool
        """
        values = {
            'authenticateTestRequest': {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key
                },
            }
        }

        response = self._authorize_request(values)
        if response and response.get('err_code'):
            return False
        return True

    # Client Key
    def get_client_secret(self):
        """ Create a client secret that will be needed for the AcceptJS integration. """
        values = {
            "getMerchantDetailsRequest": {
                "merchantAuthentication": {
                    "name": self.name,
                    "transactionKey": self.transaction_key,
                }
            }
        }
        response = self._authorize_request(values)
        client_secret = response.get('publicClientKey')
        return client_secret
