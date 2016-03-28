# -*- coding: utf-'8' "-*-"

import datetime
import logging
import time
import urllib2
from lxml import etree, objectify
from pprint import pformat
from urllib import urlencode

from odoo import api, models, _
from odoo.fields import Date
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_ogone.data import ogone_errors

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46]   # 3DS HTML response
    _ogone_cancel_tx_status = [1]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _ogone_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. Create a payment method if an alias is returned."""
        reference, pay_id, shasign, alias = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN'), data.get('ALIAS')
        if not reference or not pay_id or not shasign:
            error_msg = _('Ogone: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find transaction -> @TDENOTE use paytid ?
        transaction = self.search([('reference', '=', reference)])
        if not transaction or len(transaction) > 1:
            error_msg = _('Ogone: received data for reference %s') % (reference)
            if not transaction:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = transaction.acquirer_id._ogone_generate_shasign('out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Ogone: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        if not transaction.acquirer_reference:
            transaction.acquirer_reference = pay_id

        # alias was created on ogone server, store it
        if alias:
            PaymentMethod = self.env['payment.method']
            domain = [('acquirer_ref', '=', alias)]
            cardholder = data.get('CN')
            if not PaymentMethod.search_count(domain):
                _logger.info('Ogone: saving alias %s for partner %s' % (data.get('CARDNO'), transaction.partner_id))
                payment_method = PaymentMethod.create({
                      'name': data.get('CARDNO') + (' - ' + cardholder if cardholder else ''),
                      'partner_id': transaction.partner_id.id,
                      'acquirer_id': transaction.acquirer_id.id,
                      'acquirer_ref': alias
                })
                transaction.write({'payment_method_id': payment_method.id})

        return transaction

    @api.v7
    def _ogone_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        return PaymentTransaction._ogone_form_get_invalid_parameters(tx, data)

    @api.v8
    def _ogone_form_get_invalid_parameters(self, data):
        self.ensure_one()
        invalid_parameters = []
        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('PAYID') != self.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), self.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters


    @api.v7
    def _ogone_form_validate(self, cr, uid, tx, data, context=None):
        return PaymentTransaction._ogone_form_validate(self.browse(cr, uid, tx.id, context=context), data)

    @api.v8
    def _ogone_form_validate(self, data):
        self.ensure_one()

        if self.state == 'done':
            _logger.info('Ogone: trying to validate an already validated transaction (ref %s)', self.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            vals = {
                'state': 'done',
                'date_validate': Date.to_string(datetime.datetime.strptime(data['TRXDATE'], '%m/%d/%y')),
                'acquirer_reference': data['PAYID'],
            }
            if data.get('ALIAS') and self.partner_id and self.type == 'form_save' and not self.payment_method_id:
                payment_method = self.pool['payment.method'].create({
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': data.get('ALIAS'),
                    'name': '%s - %s' % (data.get('CARDNO'), data.get('CN'))
                })
                vals.update(payment_method_id=payment_method.id)
            self.write(vals)
            if self.callback_eval:
                safe_eval(self.callback_eval, {'self': self})
            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('PAYID'),
            })
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone_errors.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('PAYID'),
            })
            return False

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------
    @api.multi
    def ogone_s2s_do_transaction(self, **kwargs):
        # TODO: create transaction with s2s type
        self.ensure_one()
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': long(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'SAL',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': self.payment_method_id.acquirer_ref,
            'RTIMEOUT': 30,
        }

        if kwargs.get('3d_secure'):
            data.update({
                'FLAG3D': 'Y',
                'LANGUAGE': self.partner_id.lang or 'en_US',
            })

            for url in 'accept decline exception'.split():
                key = '{0}_url'.format(url)
                val = kwargs.pop(key, None)
                if val:
                    key = '{0}URL'.format(url).upper()
                    data[key] = val

        data['SHASIGN'] = account._ogone_generate_shasign('in', data)

        direct_order_url = 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % (self.acquirer_id.environment)

        _logger.debug("Ogone data %s", pformat(data))
        request = urllib2.Request(direct_order_url, urlencode(data))
        result = urllib2.urlopen(request).read()
        _logger.debug('Ogone response = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        return self._ogone_s2s_validate_tree(tree)

    @api.v7
    def _ogone_s2s_validate(self, tx):
        return PaymentTransaction._ogone_s2s_validate(tx)

    @api.v8
    def _ogone_s2s_validate(self):
        tree = self._ogone_s2s_get_tx_status()
        return self._ogone_s2s_validate_tree(tree)

    @api.v7
    def _ogone_s2s_validate_tree(self, tx, tree, tries=2):
        return PaymentTransaction._ogone_s2s_validate_tree(tx, tree, tries=tries)

    @api.v8
    def _ogone_s2s_validate_tree(self, tree, tries=2):
        self.ensure_one()
        if self.state not in ('draft', 'pending'):
            _logger.info('Ogone: trying to validate an already validated transaction (ref %s)', self.reference)
            return True

        status = int(tree.get('STATUS') or 0)
        if status in self._ogone_valid_tx_status:
            self.write({
                'state': 'done',
                'date_validate': Date.today(),
                'acquirer_reference': tree.get('PAYID'),
            })
            if tree.get('ALIAS') and self.partner_id and self.type == 'form_save' and not self.payment_method_id:
                pm = self.env['payment.method'].create({
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': tree.get('ALIAS'),
                    'name': tree.get('CARDNO'),
                })
                self.write({'payment_method_id': pm.id})
            if self.callback_eval:
                safe_eval(self.callback_eval, {'self': self})
            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': tree.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': tree.get('PAYID'),
                'html_3ds': str(tree.HTML_ANSWER).decode('base64')
            })
        elif (not status or status in self._ogone_wait_tx_status) and tries > 0:
            time.sleep(500)
            self.write({'acquirer_reference': tree.get('PAYID')})
            tree = self._ogone_s2s_get_tx_status()
            return self._ogone_s2s_validate_tree(tree, tries - 1)
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': tree.get('NCERRORPLUS'),
                'error_code': tree.get('NCERROR'),
                'error_msg': ogone_errors.OGONE_ERROR_MAP.get(tree.get('NCERROR')),
            }
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree.get('PAYID'),
            })
            return False

    @api.v7
    def _ogone_s2s_get_tx_status(self, tx):
        return PaymentTransaction._ogone_s2s_get_tx_status(tx)

    @api.v8
    def _ogone_s2s_get_tx_status(self):
        self.ensure_one()
        account = self.acquirer_id

        data = {
            'PAYID': self.acquirer_reference,
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
        }

        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (account.environment)

        _logger.debug("Ogone data %s", pformat(data))
        request = urllib2.Request(query_direct_url, urlencode(data))
        result = urllib2.urlopen(request).read()
        _logger.debug('Ogone response = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        return tree
