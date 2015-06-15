import cgi
import urllib2
import ssl
from datetime import datetime, timedelta

from openerp import models, api, service
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

soap_header = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mer="http://www.mercurypay.com"><soapenv:Header/><soapenv:Body><mer:CreditTransaction><mer:tran>'
soap_footer = '</mer:tran><mer:pw>xyz</mer:pw></mer:CreditTransaction></soapenv:Body></soapenv:Envelope>'

class MercuryTransaction(models.Model):
    _name = 'card_reader.mercury_transaction'

    def _unescape_html(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        # this has to be last:
        s = s.replace("&amp;", "&")
        return s

    def _get_pos_session(self):
        pos_session = self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)])
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

    def _setup_request(self, data):
        pos_session = self._get_pos_session()

        if not pos_session:
            return 0

        config = pos_session.config_id
        card_reader_config = self._get_card_reader_config_id(config, data['journal_id'])

        if not card_reader_config:
            return 0

        data['url_base_action'] = card_reader_config.url_base_action
        data['payment_server'] = card_reader_config.payment_server
        data['merchant_pwd'] = card_reader_config.merchant_pwd
        data['operator_id'] = pos_session.user_id.login
        data['merchant_id'] = card_reader_config.merchant_id
        data['memo'] = "Odoo " + service.common.exp_version()['server_version']

    def _do_request(self, template, data):
        xml_transaction = self.env.ref(template).render(data)
        print '------------SENDING-------------'
        print xml_transaction
        print '--------------------------------'
        xml_transaction = soap_header + cgi.escape(xml_transaction) + soap_footer

        response = ''

        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': data['url_base_action'] + '/CreditTransaction',
        }

        r = urllib2.Request(data['payment_server'], data=xml_transaction, headers=headers)
        try:
            u = urllib2.urlopen(r, timeout=65)
            response = self._unescape_html(u.read())
        except (urllib2.URLError, ssl.SSLError):
            response = "timeout"

        print '--------------RECV--------------'
        print response
        print '--------------------------------'
        return response

    def _do_reversal_or_voidsale(self, data, is_voidsale):
        self._setup_request(data)
        data['is_voidsale'] = is_voidsale
        response = self._do_request('card_reader.mercury_voidsale', data)
        return response

    @api.model
    def do_payment(self, data):
        self._setup_request(data)
        response = self._do_request('card_reader.mercury_transaction', data)
        return response

    @api.model
    def do_reversal(self, data):
        return self._do_reversal_or_voidsale(data, False)

    @api.model
    def do_voidsale(self, data):
        return self._do_reversal_or_voidsale(data, True)

    def do_return(self, data):
        self._setup_request(data)
        response = self._do_request('card_reader.mercury_return', data)
        return response

    # One time (the ones we use) Mercury tokens are required to be
    # deleted after 6 months
    @api.model
    def cleanup_old_tokens(self):
        for order in self.env['pos.order'].search([]):
            if datetime.strptime(order.create_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=6 * 30) < datetime.now():
                order.ref_no = ""
                order.record_no = ""
