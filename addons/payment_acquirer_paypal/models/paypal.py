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
from openerp.tools.float_utils import float_compare

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
        if tx_custom_values and tx_custom_values.get('return_url'):
            tx_values['custom'] = 'return_url=%s' % tx_custom_values.pop('return_url')
        if tx_custom_values:
            tx_values.update(tx_custom_values)
        return tx_values


class TxPaypal(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'paypal_txn_id': fields.char('Transaction ID'),
        'paypal_txn_type': fields.char('Transaction type'),
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

    def _paypal_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('item_number'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = 'Paypal: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        return tx

    def paypal_form_feedback(self, cr, uid, data, context=None):
        invalid_parameters = []

        # get tx
        tx = self._paypal_get_tx_from_data(cr, uid, data, context=context)

        if data.get('notify_version')[0] != '2.6':
            _logger.warning(
                'Received a notification from Paypal with version %s instead of 2.6. This could lead to issues when managing it.' %
                data.get('notify_version')
            )
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Paypal using sandbox'
            ),
        # check what is buyed
        if float_compare(float(data.get('mc_gross', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('mc_gross', tx.amount))
        if data.get('mc_currency') != tx.currency_id.name:
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

        if invalid_parameters:
            _warn_message = 'The following transaction parameters are incorrect:\n'
            for item in invalid_parameters:
                _warn_message += '\t%s: received %s instead of %s\n' % (item, data.get(item[0]), item[1])
            _logger.warning(_warn_message)
            return False

        status = data.get('payment_status', 'Pending')
        if status in ['Completed', 'Processed']:
            tx.write({
                'state': 'done',
                'txn_id': data['txn_id'],
                'date_validate': data.get('payment_date', fields.datetime.now()),
                'paypal_txn_type': data.get('express_checkout')
            })
            return True
        elif status in ['Pending', 'Expired']:
            tx.write({
                'state': 'pending',
                'txn_id': data['txn_id'],
            })
            return True
        else:
            error = 'Paypal: feedback error'
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error
            })
            return False
