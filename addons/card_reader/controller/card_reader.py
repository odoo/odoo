# -*- coding: utf-8 -*-
import logging
import werkzeug.utils
import urllib2
from urllib2 import HTTPError
from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

soap_header = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mer="http://www.mercurypay.com"><soapenv:Header/><soapenv:Body><mer:CreditTransaction><mer:tran>'
soap_footer = '</mer:tran><mer:pw>xyz</mer:pw></mer:CreditTransaction></soapenv:Body></soapenv:Envelope>'

class CardReader(http.Controller):

    @http.route('/pos/send_payement_transaction', type='json', auth='user')
    def a(self, **k):
        cr, uid, context, session = request.cr, request.uid, request.context, request.session

        # if user not logged in, log him in
        if not session.uid:
            return 0

        PosSession = request.registry['pos.session']
        pos_session_ids = PosSession.search(cr, uid, [('state', '=', 'opened'), ('user_id', '=', session.uid)], context=context)
        if not pos_session_ids:
            return 0
        PosSession.login(cr, uid, pos_session_ids, context=context)

        pos_session = request.env['pos.session'].browse(pos_session_ids)[0]

        config = pos_session.config_id
        card_reader_config = config.card_reader_config_id

        if not config.card_reader:
            return 0

        k['url_base_action'] = card_reader_config.url_base_action
        k['payment_server'] = card_reader_config.payment_server
        k['merchant_pwd'] = card_reader_config.merchant_pwd
        k['operator_id'] = config.operator_id
        k['merchant_id'] = card_reader_config.merchant_id
        k['memo'] = card_reader_config.memo

        xml_transaction = request.registry["ir.ui.view"].render(cr, uid, 'card_reader.mercury_transaction', k, context=context)

        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction':   k['url_base_action']+'/'+k['action'],
        }
        print xml_transaction

        xml_transaction = xml_transaction.replace("<", "&lt;")
        xml_transaction = xml_transaction.replace(">", "&gt;")
        xml_transaction = soap_header+xml_transaction+soap_footer

        response = ''
        print headers
        print k['payment_server']
        try:
            r = urllib2.Request(k['payment_server'], data=xml_transaction, headers=headers)

            u = urllib2.urlopen(r)
            response = u.read()
        except HTTPError as e:
            print e.code
            response = e.read()
            print response

        return response
