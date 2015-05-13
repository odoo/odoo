# -*- coding: utf-8 -*-
import logging
import urllib2
import cgi
from urllib2 import HTTPError
from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

soap_header = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mer="http://www.mercurypay.com"><soapenv:Header/><soapenv:Body><mer:CreditTransaction><mer:tran>'
soap_footer = '</mer:tran><mer:pw>xyz</mer:pw></mer:CreditTransaction></soapenv:Body></soapenv:Envelope>'

class CardReader(http.Controller):
    def _unescape_html(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        # this has to be last:
        s = s.replace("&amp;", "&")
        return s

    def _get_pos_session(self):
        session = request.session

        # if user not logged in exit fail
        if not session.uid:
            return 0

        pos_session = request.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', session.uid)])
        if not pos_session:
            return 0

        pos_session.login()

        return pos_session

    def _get_card_reader_config_id(self, config, journal_id):
        journal = config.journal_ids.filtered(lambda r: r.id == journal_id)

        if journal and journal.card_reader_config_id:
            return journal.card_reader_config_id
        else:
            return 0

    def _do_request(self, template, data):
        xml_transaction = request.env.ref(template).render(data)
        xml_transaction = soap_header + cgi.escape(xml_transaction) + soap_footer
        print '------------SENDING-------------'
        print xml_transaction
        print '--------------------------------'

        response = ''

        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': data['url_base_action'] + '/CreditTransaction',
        }

        try:
            r = urllib2.Request(data['payment_server'], data=xml_transaction, headers=headers)
            u = urllib2.urlopen(r)
            response = self._unescape_html(u.read())
        except HTTPError as e:
            print e.code
            response = e.read()

        print '--------------RECV--------------'
        print response
        print '--------------------------------'
        return response

    @http.route('/pos/send_payment_transaction', type='json', auth='user')
    def payment_handler(self, **k):
        pos_session = self._get_pos_session()

        if not pos_session:
            return 0

        config = pos_session.config_id
        card_reader_config = self._get_card_reader_config_id(config, k['journal_id'])

        if not card_reader_config:
            return 0

        k['url_base_action'] = card_reader_config.url_base_action
        k['payment_server'] = card_reader_config.payment_server
        k['merchant_pwd'] = card_reader_config.merchant_pwd
        k['operator_id'] = pos_session.user_id.login
        k['merchant_id'] = card_reader_config.merchant_id
        k['config_id'] = config.id
        k['memo'] = card_reader_config.memo

        response = self._do_request('card_reader.mercury_transaction', k)
        return response

    @http.route('/pos/send_reversal', type='json', auth='user')
    def reversal_handler(self, **k):
        pos_session = self._get_pos_session()

        if not pos_session:
            return 0

        config = pos_session.config_id
        card_reader_config = self._get_card_reader_config_id(config, k['journal_id'])

        if not card_reader_config:
            return 0

        k['url_base_action'] = card_reader_config.url_base_action
        k['payment_server'] = card_reader_config.payment_server
        k['merchant_pwd'] = card_reader_config.merchant_pwd
        k['operator_id'] = pos_session.user_id.login
        k['merchant_id'] = card_reader_config.merchant_id
        k['config_id'] = config.id
        k['memo'] = card_reader_config.memo

        response = self._do_request('card_reader.mercury_reversal', k)
        return response
