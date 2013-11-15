# -*- coding: utf-'8' "-*-"
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.payment_acquirer_paypal.controllers.main import PaypalController
from openerp.osv import osv, fields

import logging
import requests
import urlparse

_logger = logging.getLogger(__name__)


class AcquirerPaypal(osv.Model):
    _inherit = 'payment.acquirer'

    _columns = {
        'paypal_email_id': fields.char('Email ID', required_if_provider='paypal'),
        'paypal_username': fields.char('Username', required_if_provider='paypal'),
        'paypal_password': fields.char('Password'),
        'paypal_signature': fields.char('Signature'),
        'paypal_tx_url': fields.char('Transaction URL', required_if_provider='paypal'),
        'paypal_use_dpn': fields.boolean('Use DPN'),
        'paypal_use_ipn': fields.boolean('Use IPN'),
    }

    _defaults = {
        'paypal_use_dpn': True,
        'paypal_use_ipn': True,
        'paypal_tx_url': 'https://www.sandbox.paypal.com/cgi-bin/webscr',
    }

    def paypal_form_generate_values(self, cr, uid, id, reference, amount, currency, partner_id=False, partner_values=None, tx_custom_values=None, context=None):
        if partner_values is None:
            partner_values = {}
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        partner = None
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
        tx_values = {
            'cmd': '_xclick',
            'business': acquirer.paypal_email_id,
            'item_name': reference,
            'item_number': reference,
            'amount': amount,
            'currency_code': currency and currency.name or 'EUR',
            'address1': partner and ' '.join((partner.street or '', partner.street2 or '')).strip() or ' '.join((partner_values.get('street', ''), partner_values.get('street2', ''))).strip(),
            'city': partner and partner.city or partner_values.get('city', ''),
            'country': partner and partner.country_id and partner.country_id.name or partner_values.get('country_name', ''),
            'email': partner and partner.email or partner_values.get('email', ''),
            'zip': partner and partner.zip or partner_values.get('zip', ''),
            'first_name': partner and partner.name or partner_values.get('name', '').split()[-1:],
            'last_name': partner and partner.name or partner_values.get('name', '').split()[:-1],
            'return': '%s' % urlparse.urljoin(base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
        }
        if tx_custom_values:
            tx_values.update(tx_custom_values)
        return tx_values


class TxPaypal(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'paypal_txn_id': fields.char('Transaction ID'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def paypal_form_generate_values(self, cr, uid, id, tx_custom_values=None, context=None):
        tx = self.browse(cr, uid, id, context=context)

        tx_data = {
            'item_name': tx.name,
            'first_name': tx.partner_name and tx.partner_name.split()[-1:],
            'last_name': tx.partner_name and tx.partner_name.split()[:-1],
            'email': tx.partner_email,
            'zip': tx.partner_zip,
            'address1': tx.partner_address,
            'city': tx.partner_city,
            'country': tx.partner_country_id and tx.partner_country_id.name or '',
        }
        if tx_custom_values:
            tx_data.update(tx_custom_values)
        return self.pool['payment.acquirer'].paypal_form_generate_values(
            cr, uid, tx.acquirer_id.id,
            tx.reference, tx.amount, tx.currency_id,
            tx_custom_values=tx_data,
            context=context
        )



    def validate_paypal_notification(self, cr, uid, url, context=None):
        parsed_url = urlparse.urlparse(url)
        query_parameters = parsed_url.query
        parameters = urlparse.parse_qs(query_parameters)

        invalid_parameters = []

        # check tx effectively exists
        txn_id = parameters.get('txn_id')[0]
        tx_ids = self.search(cr, uid, [('paypal_txn_id', '=', txn_id)], context=context)
        if not tx_ids:
            _logger.warning(
                'Received a notification from Paypal for a tx %s that does not exists in database.' %
                txn_id
            )
            return False
        elif len(tx_ids) > 1:
            _logger.warning(
                'Received a notification from Paypal for a tx %s that is duplicated in database.' %
                txn_id
            )

        tx = self.browse(cr, uid, tx_ids[0], context=context)

        if parameters.get('notify_version')[0] != '2.6':
            _logger.warning(
                'Received a notification from Paypal with version %s instead of 2.6. This could lead to issues when managing it.' %
                parameters.get('notify_version')
            )
        if parameters.get('test_ipn')[0]:
            _logger.warning(
                'Received a notification from Paypal using sandbox'
            ),
        # check transaction
        if parameters.get('payment_status')[0] != 'Completed':
            invalid_parameters.append(('payment_status', 'Completed'))
        # check what is buyed
        if parameters.get('mc_gross')[0] != tx.amount:
            invalid_parameters.append(('mc_gross', tx.amount))
        if parameters.get('mc_currency')[0] != tx.currency_id.name:
            invalid_parameters.append(('mc_currency',  tx.currency_id.name))
        # if parameters.get('payment_fee') != tx.payment_fee:
            # invalid_parameters.append(('payment_fee',  tx.payment_fee))
        # if parameters.get('quantity') != tx.quantity:
            # invalid_parameters.append(('mc_currency',  tx.quantity))
        # if parameters.get('shipping') != tx.shipping:
            # invalid_parameters.append(('shipping',  tx.shipping))
        # check buyer
        # if parameters.get('payer_id') != tx.payer_id:
            # invalid_parameters.append(('mc_gross', tx.payer_id))
        # if parameters.get('payer_email') != tx.payer_email:
            # invalid_parameters.append(('payer_email', tx.payer_email))
        # check seller
        # if parameters.get('receiver_email') != tx.receiver_email:
            # invalid_parameters.append(('receiver_email', tx.receiver_email))
        # if parameters.get('receiver_id') != tx.receiver_id:
            # invalid_parameters.append(('receiver_id', tx.receiver_id))

        if not invalid_parameters:
            self.write(cr, uid, [tx.id], {
                'payment_type': parameters.get('payment_type')[0],
                'date_validate': parameters.get('payment_date', [fields.datetime.now()])[0],
                'txn_type': parameters.get('express_checkout')[0],
            }, context=context)
            return tx.id
        else:
            _warn_message = 'The following transaction parameters are incorrect:\n'
            for item in invalid_parameters:
                _warn_message += '\t%s: received %s instead of %s\n' % (item[0], parameters.get(item[0])[0], item[1])
            _logger.warning(_warn_message)

        return False

    def create_paypal_command(self, cr, uid, cmd, parameters):
        parameters.update(cmd=cmd)
        return requests.post(self._paypal_url, data=parameters)

    def _validate_paypal(self, cr, uid, ids, context=None):
        res = []
        for tx in self.browse(cr, uid, ids, context=context):
            parameters = {}
            parameters.update(
                cmd='_notify-validate',
                business='tdelavallee-facilitator@gmail.com',
                item_name="%s %s" % ('cacapoutch', tx.reference),
                item_number=tx.reference,
                amount=tx.amount,
                currency_code=tx.currency_id.name,
            )
            print '\t', parameters
            # paypal_url = "https://www.paypal.com/cgi-bin/webscr"
            paypal_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
            resp = requests.post(paypal_url, data=parameters)
            print resp
            print resp.url
            print resp.text
            response = urlparse.parse_qsl(resp)
            print response
            # transaction's unique id
            # response["txn_id"]

            # "Failed", "Reversed", "Refunded", "Canceled_Reversal", "Denied"
            status = "refused"
            retry_time = False

            if response["payment_status"] == "Voided":
                status = "refused"
            elif response["payment_status"] in ("Completed", "Processed") and response["item_number"] == tx.reference and response["mc_gross"] == tx.amount:
                status = "validated"
            elif response["payment_status"] in ("Expired", "Pending"):
                status = "pending"
                retry_time = 60

            res.append(
                (status, retry_time, "payment_status=%s&pending_reason=%s&reason_code=%s" % (
                    response["payment_status"],
                    response.get("pending_reason"),
                    response.get("reason_code")))
            )
        return response
