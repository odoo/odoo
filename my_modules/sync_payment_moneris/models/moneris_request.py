# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import logging
import requests

from urllib.request import URLError
import xml.etree.ElementTree as etree

_logger = logging.getLogger(__name__)


class MonerisRequest(object):
    def __init__(self, store_id, api_token):
        self.store_id = store_id
        self.api_token = api_token

    def _get_data(self):
        pass

    def _parse_response_body(self, root):
        pass

    def send(self):
        """
        This Method is used to send request to Moneris and returns the Response
        sent by Moneris.
        """
        datas = self._get_data()
        data = datas[0]
        api_url = datas[1]

        response = {}
        try:
            response_text = requests.post(api_url, data=data, headers={'Content-Type': 'text/xml'})
            response = self.__parse_response(response_text.content)
        except URLError as e:
            if hasattr(e, 'reason'):
                _logger.info('Could not reach the server, reason: %s' % str(e.reason))
            elif hasattr(e, 'code'):
                _logger.info('Could not fulfill the request, code: %s' % str(e.code))
        return response

    def __parse_response(self, response_text):
        root = etree.fromstring(response_text)
        return self._parse_response_body(root)


class MonerisPurchaseRequest(MonerisRequest):
    def __init__(self, store_id, api_token, data_key, order_id,
                 customer_id, amount, email, first_name,
                 street, city, state, zip, country,
                 phone_number, order_lines, trxn_type,
                 provider_id, is_invoice_payment=None, is_sale_payment=None):
        self.data_key = data_key
        self.order_id = order_id
        self.customer_id = customer_id
        self.amount = amount
        self.email = email
        self.first_name = first_name
        self.address = street
        self.city = city
        self.province = state
        self.postal_code = zip
        self.country = country
        self.phone_number = phone_number
        self.order_lines = order_lines
        self.trxn_type = trxn_type
        self.provider_id = provider_id
        self.is_invoice_payment = is_invoice_payment
        self.is_sale_payment = is_sale_payment
        super(MonerisPurchaseRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send Purchase request.
        """
        data = []
        product_data = ""
        order_lines = self.order_lines.filtered(lambda x: x.product_id)
        if order_lines:
            # Sale Order Line Product Data
            if self.is_sale_payment:
                for line in order_lines:
                    product_name = line.product_id.name or '' if (line.price_subtotal >= 0 and line.product_uom_qty > 0.0) else line.product_id.name + " (The product price is negative, so the amount is deducted from the Subtotal)"
                    quantity = abs(line.product_uom_qty)
                    product_code = line.product_id.default_code or ''
                    product_amount = abs(line.price_subtotal)
                    product_data = product_data + """<item>
                            <name>%s</name>
                            <quantity>%s</quantity>
                            <product_code>%s</product_code>
                            <extended_amount>%s</extended_amount>
                        </item>""" % (product_name, quantity, product_code, product_amount)
            elif self.is_invoice_payment:
                # Invoice Line Product Data
                for line in order_lines:
                    product_name = line.product_id.name or '' if (line.price_subtotal >= 0 and line.quantity > 0.0) else line.product_id.name + " (The product price is negative, so the amount is deducted from the Subtotal)"
                    quantity = abs(line.quantity)
                    product_code = line.product_id.default_code
                    product_amount = abs(line.price_subtotal)
                    product_data = product_data + """<item>
                            <name>%s</name>
                            <quantity>%s</quantity>
                            <product_code>%s</product_code>
                            <extended_amount>%s</extended_amount>
                        </item>""" % (product_name, quantity, product_code, product_amount)
        payment_data = """
        <?xml version="1.0"?>
        <request>
            <store_id>%s</store_id>
            <api_token>%s</api_token>
            <%s>
                <data_key>%s</data_key>
                <order_id>%s</order_id>
                <cust_id>%s</cust_id>
                <amount>%s</amount>
                <crypt_type>7</crypt_type>
                <cust_info>
                    <email>%s</email>
                    <instructions>Make it fast</instructions>
                    <billing>
                        <first_name>%s</first_name>
                        <last_name></last_name>
                        <company_name></company_name>
                        <address>%s</address>
                        <city>%s</city>
                        <province>%s</province>
                        <postal_code>%s</postal_code>
                        <country>%s</country>
                        <phone_number>%s</phone_number>
                        <fax></fax>
                        <tax1></tax1>
                        <tax2></tax2>
                        <tax3></tax3>
                        <shipping_cost></shipping_cost>
                    </billing>""" % (self.store_id, self.api_token, self.trxn_type, self.data_key, self.order_id,
                                     self.customer_id, self.amount, self.email, self.first_name, self.address,
                                     self.city, self.province, self.postal_code, self.country,
                                     self.phone_number)
        shipping_data = """
                    <shipping>
                        <first_name>%s</first_name>
                        <last_name></last_name>
                        <company_name></company_name>
                        <address>%s</address>
                        <city>%s</city>
                        <province>%s</province>
                        <postal_code>%s</postal_code>
                        <country>%s</country>
                        <phone_number>%s</phone_number>
                        <fax></fax>
                        <tax1></tax1>
                        <tax2></tax2>
                        <tax3></tax3>
                        <shipping_cost></shipping_cost>
                    </shipping>""" % (self.first_name, self.address, self.city, self.province,
                                      self.postal_code, self.country, self.phone_number)
        product_data = """ %s %s %s
                </cust_info>
            </%s>
        </request>""" % (payment_data, shipping_data, product_data, self.trxn_type)
        data.append(product_data)
        environment = 'prod' if self.provider_id.state == 'enabled' else 'test'
        url = self.provider_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisPurchaseResponse().get_response(root)


class MonerisPurchaseResponse(object):

    def get_response(self, root):
        complete = root.find('receipt/Complete').text
        if complete != 'false':
            response = {
                'receipt_id': root.find('receipt/ReceiptId').text,
                'reference_num': root.find('receipt/ReferenceNum').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'trans_time': root.find('receipt/TransTime').text,
                'trans_date': root.find('receipt/TransDate').text,
                'trans_amount': root.find('receipt/TransAmount').text,
                'cardtype': root.find('receipt/CardType').text,
                'payment_type': root.find('receipt/PaymentType').text,
                'cust_id': root.find('receipt/ResolveData/cust_id').text,
                'expdate': root.find('receipt/ResolveData/expdate').text,
                'cc_number': root.find('receipt/ResolveData/masked_pan').text,
                'trans_type': root.find('receipt/TransType').text,
                'trans_id': root.find('receipt/TransID').text,
                'api_request': True,
            }
        else:
            response = {
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'api_request': True,
                'error': True,
                'tx_type': 'purchase',
            }
        return response


class MonerisAuthorizeRequest(MonerisRequest):
    def __init__(self, store_id, api_token, data_key, order_id, amount, customer_id, provider_id):
        self.data_key = data_key
        self.order_id = order_id
        self.amount = amount
        self.customer_id = customer_id
        self.provider_id = provider_id
        super(MonerisAuthorizeRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send Authorize request.
        """
        data = []
        request_data = """
            <?xml version="1.0"?>
                <request>
                    <store_id>%s</store_id>
                    <api_token>%s</api_token>
                    <res_preauth_cc>
                        <data_key>%s</data_key>
                        <order_id>%s</order_id>
                        <cust_id>%s</cust_id>
                        <amount>%s</amount>
                        <crypt_type>7</crypt_type>
                    </res_preauth_cc>
                </request>""" % (self.store_id, self.api_token, self.data_key, self.order_id,
                                 self.customer_id, self.amount)
        data.append(request_data)
        environment = 'prod' if self.provider_id.state == 'enabled' else 'test'
        url = self.provider_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisAuthorizeResponse().get_response(root)


class MonerisAuthorizeResponse(object):

    def get_response(self, root):
        complete = root.find('receipt/Complete').text
        if complete != 'false':
            response = {
                'receipt_id': root.find('receipt/ReceiptId').text,
                'reference_num': root.find('receipt/ReferenceNum').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'trans_time': root.find('receipt/TransTime').text,
                'trans_date': root.find('receipt/TransDate').text,
                'trans_amount': root.find('receipt/TransAmount').text,
                'cardtype': root.find('receipt/CardType').text,
                'trans_type': root.find('receipt/TransType').text,
                'trans_id': root.find('receipt/TransID').text,
                'cust_id': root.find('receipt/ResolveData/cust_id').text,
                'expdate': root.find('receipt/ResolveData/expdate').text,
                'cc_number': root.find('receipt/ResolveData/masked_pan').text,
                'payment_type': root.find('receipt/PaymentType').text,
                'api_request': True,
            }
        else:
            response = {
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'api_request': True,
                'error': True,
                'tx_type': 'authorize',
            }
        return response


class MonerisCaptureRequest(MonerisRequest):
    def __init__(self, store_id, api_token, order_id, comp_amount, txn_number, provider_id):
        self.order_id = order_id
        self.comp_amount = comp_amount
        self.txn_number = txn_number
        self.provider_id = provider_id
        super(MonerisCaptureRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send a capture request.
        """
        data = []
        request_data = """
            <?xml version="1.0"?>
            <request>
                <store_id>%s</store_id>
                <api_token>%s</api_token>
                <completion>
                    <order_id>%s</order_id>
                    <comp_amount>%s</comp_amount>
                    <txn_number>%s</txn_number>
                    <crypt_type>7</crypt_type>
                </completion>
            </request>""" % (self.store_id, self.api_token, self.order_id,
                                 self.comp_amount, self.txn_number)
        data.append(request_data)
        environment = 'prod' if self.provider_id.state == 'enabled' else 'test'
        url = self.provider_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisCaptureResponse().get_response(root)


class MonerisCaptureResponse(object):

    def get_response(self, root):
        complete = root.find('receipt/Complete').text
        if complete != 'false':
            response = {
                'receipt_id': root.find('receipt/ReceiptId').text,
                'reference_num': root.find('receipt/ReferenceNum').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'trans_time': root.find('receipt/TransTime').text,
                'trans_date': root.find('receipt/TransDate').text,
                'trans_amount': root.find('receipt/TransAmount').text,
                'cardtype': root.find('receipt/CardType').text,
                'trans_type': root.find('receipt/TransType').text,
                'trans_id': root.find('receipt/TransID').text,
                'api_request': True,
            }
        else:
            response = {
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'api_request': True,
                'error': True,
                'tx_type': 'capture',
            }
        return response


class MonerisRefundRequest(MonerisRequest):
    def __init__(self, store_id, api_token, order_id, amount_total, txn_number, provider_id):
        self.order_id = order_id
        self.amount_total = amount_total
        self.txn_number = txn_number
        self.provider_id = provider_id
        super(MonerisRefundRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send a refund request.
        """
        data = []
        request_data = """
            <?xml version="1.0"?>
                <request>
                    <store_id>%s</store_id>
                    <api_token>%s</api_token>
                    <refund>
                        <order_id>%s</order_id>
                        <amount>%s</amount>
                        <txn_number>%s</txn_number>
                        <crypt_type>1</crypt_type>
                    </refund>
                </request>""" % (self.store_id, self.api_token, self.order_id,
                                 self.amount_total, self.txn_number)
        data.append(request_data)
        environment = 'prod' if self.provider_id.state == 'enabled' else 'test'
        url = self.provider_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisRefundResponse().get_response(root)


class MonerisRefundResponse(object):

    def get_response(self, root):
        complete = root.find('receipt/Complete').text
        if complete != 'false':
            response = {
                'receipt_id': root.find('receipt/ReceiptId').text,
                'reference_num': root.find('receipt/ReferenceNum').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'trans_time': root.find('receipt/TransTime').text,
                'trans_date': root.find('receipt/TransDate').text,
                'trans_amount': root.find('receipt/TransAmount').text,
                'cardtype': root.find('receipt/CardType').text,
                'trans_type': root.find('receipt/TransType').text,
                'trans_id': root.find('receipt/TransID').text,
                'api_request': True,
            }
        else:
            response = {
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'api_request': True,
                'error': True,
                'tx_type': 'refund',
            }
        return response


class MonerisVoidRequest(MonerisRequest):
    def __init__(self, store_id, api_token, order_id, txn_number, provider_id):
        self.order_id = order_id
        self.txn_number = txn_number
        self.provider_id = provider_id
        super(MonerisVoidRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send a void request.
        """
        data = []
        request_data = """
            <?xml version="1.0"?>
            <request>
                <store_id>%s</store_id>
                <api_token>%s</api_token>
                <purchasecorrection>
                    <order_id>%s</order_id>
                    <txn_number>%s</txn_number>
                    <crypt_type>1</crypt_type>
                </purchasecorrection>
            </request>""" % (self.store_id, self.api_token, self.order_id, self.txn_number)
        data.append(request_data)
        environment = 'prod' if self.provider_id.state == 'enabled' else 'test'
        url = self.provider_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisVoidResponse().get_response(root)


class MonerisVoidResponse(object):

    def get_response(self, root):
        complete = root.find('receipt/Complete').text
        if complete != 'false':
            response = {
                'receipt_id': root.find('receipt/ReceiptId').text,
                'reference_num': root.find('receipt/ReferenceNum').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'trans_time': root.find('receipt/TransTime').text,
                'trans_date': root.find('receipt/TransDate').text,
                'trans_amount': root.find('receipt/TransAmount').text,
                'cardtype': root.find('receipt/CardType').text,
                'trans_type': root.find('receipt/TransType').text,
                'trans_id': root.find('receipt/TransID').text,
                'api_request': True
            }
        else:
            response = {
                'message': root.find('receipt/Message').text,
                'complete': root.find('receipt/Complete').text,
                'response_code': root.find('receipt/ResponseCode').text,
                'api_request': True,
                'error': True,
                'tx_type': 'void',
            }
        return response
