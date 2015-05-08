# -*- coding: utf-8 -*-
import logging
import urllib2
from urllib2 import HTTPError
from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

soap_header = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mer="http://www.mercurypay.com"><soapenv:Header/><soapenv:Body><mer:CreditTransaction><mer:tran>'
soap_footer = '</mer:tran><mer:pw>xyz</mer:pw></mer:CreditTransaction></soapenv:Body></soapenv:Envelope>'


class CardReader(http.Controller):
    @http.route('/pos/send_payment_transaction', type='json', auth='user')
    def handler(self, **k):
        session = request.session

        # if user not logged in exit fail
        if not session.uid:
            return 0

        pos_session = request.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', session.uid)])
        if not pos_session:
            return 0

        pos_session.login()
        config = pos_session.config_id

        journal = config.journal_ids.filtered(lambda r: r.id == k['journal_id'])
        if not journal or not journal.card_reader_config_id:
            return 0

        card_reader_config = journal.card_reader_config_id

        k['url_base_action'] = card_reader_config.url_base_action
        k['payment_server'] = card_reader_config.payment_server
        k['merchant_pwd'] = card_reader_config.merchant_pwd
        k['operator_id'] = pos_session.user_id.login
        k['merchant_id'] = card_reader_config.merchant_id
        k['config_id'] = config.id
        k['memo'] = card_reader_config.memo

        xml_transaction = request.env.ref('card_reader.mercury_transaction').render(k)

        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': k['url_base_action'] + '/' + k['action'],
        }

        print xml_transaction
        xml_transaction = xml_transaction.replace("<", "&lt;")
        xml_transaction = xml_transaction.replace(">", "&gt;")
        xml_transaction = soap_header + xml_transaction + soap_footer

        response = ''

        try:
            r = urllib2.Request(k['payment_server'], data=xml_transaction, headers=headers)

            u = urllib2.urlopen(r)
            response = u.read()
        except HTTPError as e:
            print e.code
            response = e.read()
            print response

        return response
