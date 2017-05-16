# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

import requests
import werkzeug

from odoo import models, api, service
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, misc


class MercuryTransaction(models.Model):
    _name = 'pos_mercury.mercury_transaction'

    def _get_pos_session(self):
        pos_session = self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)], limit=1)
        if not pos_session:
            raise UserError("No POS session")

        pos_session.login()

        return pos_session

    def _get_pos_mercury_config_id(self, config, journal_id):
        journal = config.journal_ids.filtered(lambda r: r.id == journal_id)

        if journal and journal.pos_mercury_config_id:
            return journal.pos_mercury_config_id
        else:
            raise UserError("No Mercury configuration associated with the journal.")

    def _setup_request(self, data):
        # todo: in master make the client include the pos.session id and use that
        pos_session = self._get_pos_session()

        config = pos_session.config_id
        pos_mercury_config = self._get_pos_mercury_config_id(config, data['journal_id'])

        data['operator_id'] = pos_session.user_id.login
        data['merchant_id'] = pos_mercury_config.sudo().merchant_id
        data['merchant_pwd'] = pos_mercury_config.sudo().merchant_pwd
        data['memo'] = "Odoo " + service.common.exp_version()['server_version']

    def _do_request(self, template, data):
        xml_transaction = self.env.ref(template).render(data)

        if not data['merchant_id'] or not data['merchant_pwd']:
            return "not setup"

        soap_header = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mer="http://www.mercurypay.com"><soapenv:Header/><soapenv:Body><mer:CreditTransaction><mer:tran>'
        soap_footer = '</mer:tran><mer:pw>' + data['merchant_pwd'] + '</mer:pw></mer:CreditTransaction></soapenv:Body></soapenv:Envelope>'
        xml_transaction = soap_header + misc.escape_html(xml_transaction) + soap_footer

        response = ''

        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': 'http://www.mercurypay.com/CreditTransaction',
        }

        try:
            r = requests.post('https://w1.mercurypay.com/ws/ws.asmx', data=xml_transaction, headers=headers, timeout=65)
            r.raise_for_status()
            response = werkzeug.utils.unescape(r.content)
        except:
            response = "timeout"

        return response

    def _do_reversal_or_voidsale(self, data, is_voidsale):
        try:
            self._setup_request(data)
        except UserError:
            return "internal error"

        data['is_voidsale'] = is_voidsale
        response = self._do_request('pos_mercury.mercury_voidsale', data)
        return response

    @api.model
    def do_payment(self, data):
        try:
            self._setup_request(data)
        except UserError:
            return "internal error"

        response = self._do_request('pos_mercury.mercury_transaction', data)
        return response

    @api.model
    def do_reversal(self, data):
        return self._do_reversal_or_voidsale(data, False)

    @api.model
    def do_voidsale(self, data):
        return self._do_reversal_or_voidsale(data, True)

    def do_return(self, data):
        try:
            self._setup_request(data)
        except UserError:
            return "internal error"

        response = self._do_request('pos_mercury.mercury_return', data)
        return response

    # One time (the ones we use) Mercury tokens are required to be
    # deleted after 6 months
    @api.model
    def cleanup_old_tokens(self):
        expired_creation_date = (date.today() - timedelta(days=6 * 30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        for order in self.env['pos.order'].search([('create_date', '<', expired_creation_date)]):
            order.ref_no = ""
            order.record_no = ""
