# -*- coding: utf-8 -*-
# This code is adapted from https://github.com/drewisme/authorizesauce orginally
# published under the MIT License:
# Copyright (c) 2015 Drew Partridge (github:drewisme)
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# The adaptations made in this file are published under the LGPL license.
# See LICENSE file for full copyright and licensing details of these adaptations.
import logging
from suds.client import Client
from suds import WebFault
from ssl import SSLError
import urllib
from uuid import uuid4

_logger = logging.getLogger(__name__)
# uncomment to enable logging of SOAP requests and responses
# logging.getLogger('suds.client').setLevel(logging.DEBUG)

RESPONSE_FIELDS = {
    0: 'x_response_code',
    2: 'x_response_reason_code',
    3: 'x_response_reason_text',
    4: 'x_authorization_code',
    5: 'x_avs_response',
    6: 'x_trans_id',
    7: 'x_invoice_num',
    9: 'x_amount',
}

DELIMITER = ';'


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class AuthorizeRequest():

    def __init__(self, environment, login_id, transaction_key):
        if environment == 'prod':
            authorize_url = 'https://api.authorize.net/soap/v1/Service.asmx?WSDL'
        else:
            authorize_url = 'https://apitest.authorize.net/soap/v1/Service.asmx?WSDL'
        self.login_id = login_id
        self.transaction_key = transaction_key
        self.transaction_options = urllib.urlencode({
            'x_version': '3.1',
            'x_test_request': 'Y' if environment == 'test' else 'F',
            'x_delim_data': 'TRUE',  # asks for a response to each transaction
            'x_delim_char': DELIMITER,
        })
        self.client = Client(authorize_url)
        self.client_auth = self.client.factory.create('MerchantAuthenticationType')
        self.client_auth.name = self.login_id
        self.client_auth.transactionKey = self.transaction_key

    def _authorize_call_service(self, service, *args):
        method = getattr(self.client.service, service)
        try:
            response = method(self.client_auth, *args)
        except (WebFault, SSLError) as e:
            raise e
        return response

    def create_authorize_payment_profile(self, partner, card_number, expiration_date, card_code=None):
        """ create_authorize_payment_profile(partner, card_number, expiration_date, card_code=None) -> payment_profile

        Creates a payment profile for the partner usign the provided card data.

        While in a more complete Authorize.net library, we could specify to which
        customer profile this payment profile should be linked, this particular
        implementation simply creates a new customer profile for each payment
        profile (to avoid having to synchronise the Authorize.net backend
        everytime a change is made on the partner - i.e. address, email, etc.)

        :param record partner: the partner registering the payment profile (i.e. the customer)
        :param str card_number: credit card number (numeric characters only)
        :param str expiration_date: credit card expiration date (MMYY)
        :param str card_code: credit card CSC/CVV (3 to 4 numeric characters depending on card type)
        :rtype: payment_profile
        :return: payment_profile record.
        """
        payment_profile = self.client.factory.create('CustomerPaymentProfileType')
        customer_type_enum = self.client.factory.create('CustomerTypeEnum')
        payment_profile.billTo.firstName, payment_profile.billTo.lastName = _partner_split_name(partner.name)
        payment_profile.billTo.company = partner.commercial_partner_id.name if partner.commercial_partner_id.is_company else None
        payment_profile.customerType = customer_type_enum.company if partner.is_company else customer_type_enum.individual
        payment_profile.billTo.address = (partner.street + (partner.street2 if partner.street2 else '')) or None
        payment_profile.billTo.city = partner.city
        payment_profile.billTo.state = partner.state_id.name or None
        payment_profile.billTo.zip = partner.zip
        payment_profile.billTo.country = partner.country_id.name or None
        payment_type = self.client.factory.create('PaymentType')
        credit_card_type = self.client.factory.create('CreditCardType')
        credit_card_type.cardNumber = card_number
        credit_card_type.expirationDate = expiration_date
        credit_card_type.cardCode = card_code
        payment_type.creditCard = credit_card_type
        payment_profile.payment = payment_type
        return payment_profile

    def create_authorize_customer_profile(self, partner, payments=None):
        """ create_authorize_customer_profile(partner, payments=None) -> customer_profile_id, payment_profile_ids

        Creates a customer profile for the partner and attaches the provided payment
        profiles (if any).

        While in a more complete Authorize.net library, we could specify to which
        customer profile this payment profile should be linked, this particular
        implementation simply creates a new customer profile for each payment
        profile (to avoid having to synchronise the Authorize.net backend
        everytime a change is made on the partner - i.e. address, email, etc.)

        :param record partner: the partner registering the payment profile (i.e. the customer)
        :param list card_number: credit card number (numeric characters only)
        :rtype: tuple(long, list(long))
        :return: customer_profile id, payment_profiles ids.
        """
        profile = self.client.factory.create('CustomerProfileType')
        profile.merchantCustomerId = 'ODOO-%s-%s' % (partner.id, uuid4().hex[:8])
        profile.email = partner.email
        if payments:
            payment_array = self.client.factory.create('ArrayOfCustomerPaymentProfileType')
            payment_array.CustomerPaymentProfileType = payments
            profile.paymentProfiles = payment_array
        response = self._authorize_call_service('CreateCustomerProfile', profile, 'none')
        profile_id = response.customerProfileId
        payment_ids = response.customerPaymentProfileIdList[0]
        return profile_id, payment_ids

    def parse_authorize_response(self, response):
        response = response.split(DELIMITER)
        return {name: response[index] for index, name in RESPONSE_FIELDS.items()}

    def create_authorize_transaction(self, profile_id, payment_id, amount, invoice_number):
        """ create_authorize_transaction(profile_id, payment_id, amount, invoice_number) -> customer_profile_id, payment_profile_ids

        Process a payment transaction for the given customer profile and payment
        profile for the specified amount with the reference given in invoice_number.

        Notice that the currency is *not* specified, as currently Authorize.net
        only accepts payments in the currency set on the Authorize.net merchant account.

        :param str profile_id: customer_profile id in the authorize.net backend
        :param str payment_id: payment_profile id in the authorize.net backend
        :param float amount: amount of the transaction
        :param str invoice_number: payment.transaction reference in the Odoo backend
        :rtype: dict
        :return: parsed SOAP response
        """
        transaction = self.client.factory.create('ProfileTransactionType')
        capture = self.client.factory.create('ProfileTransAuthCaptureType')
        capture.amount = str(amount)
        capture.customerProfileId = profile_id
        capture.customerPaymentProfileId = payment_id
        capture.order.invoiceNumber = invoice_number
        transaction.profileTransAuthCapture = capture
        response = self._authorize_call_service('CreateCustomerProfileTransaction',
            transaction, self.transaction_options)
        return self.parse_authorize_response(response.directResponse)
