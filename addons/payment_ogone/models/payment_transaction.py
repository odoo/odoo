# -*- coding: utf-'8' "-*-"

import datetime
import logging
from lxml import etree, objectify
from openerp.tools.translate import _
from pprint import pformat
import time
from urllib import urlencode
import urllib2

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_ogone.data import ogone
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.float_utils import float_compare
from openerp.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class PaymentTxOgone(osv.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46]   # 3DS HTML response
    _ogone_cancel_tx_status = [1]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _ogone_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. Create a payment method if an alias is returned."""
        reference, pay_id, shasign, alias = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN'), data.get('ALIAS')
        if not reference or not pay_id or not shasign:
            error_msg = _('Ogone: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use paytid ?
        tx_ids = self.search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = _('Ogone: received data for reference %s') % (reference)
            if not tx_ids:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        # verify shasign
        shasign_check = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Ogone: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        if not tx.acquirer_reference:
            tx.acquirer_reference = pay_id

        # alias was created on ogone server, store it
        if alias:
            method_obj = self.pool['payment.method']
            domain = [('acquirer_ref', '=', alias)]
            cardholder = data.get('CN')
            if not method_obj.search_count(cr, uid, domain, context=context):
                _logger.info('Ogone: saving alias %s for partner %s' % (data.get('CARDNO'), tx.partner_id))
                ref = method_obj.create(cr, uid, {'name': data.get('CARDNO') + (' - ' + cardholder if cardholder else ''),
                                                  'partner_id': tx.partner_id.id,
                                                  'acquirer_id': tx.acquirer_id.id,
                                                  'acquirer_ref': alias
                                                  })
                tx.write({'payment_method_id': ref})

        return tx

    def _ogone_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if tx.acquirer_reference and data.get('PAYID') != tx.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), tx.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % tx.amount))
        if data.get('currency') != tx.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), tx.currency_id.name))

        return invalid_parameters

    def _ogone_form_validate(self, cr, uid, tx, data, context=None):
        if tx.state == 'done':
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', tx.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            vals = {
                'state': 'done',
                'date_validate': datetime.datetime.strptime(data['TRXDATE'], '%m/%d/%y').strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': data['PAYID'],
            }
            if data.get('ALIAS') and tx.partner_id and tx.type == 'form_save' and not tx.payment_method_id:
                pm_id = self.pool['payment.method'].create(cr, uid, {
                    'partner_id': tx.partner_id.id,
                    'acquirer_id': tx.acquirer_id.id,
                    'acquirer_ref': data.get('ALIAS'),
                    'name': '%s - %s' % (data.get('CARDNO'), data.get('CN'))
                }, context=context)
                vals.update(payment_method_id=pm_id)
            tx.write(vals)
            if tx.callback_eval:
                safe_eval(tx.callback_eval, {'self': tx})
            return True
        elif status in self._ogone_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': data.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('PAYID'),
            })
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('PAYID'),
            })
            return False

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------
    def ogone_s2s_do_transaction(self, cr, uid, id, context=None, **kwargs):
        # TODO: create tx with s2s type
        tx = self.browse(cr, uid, id, context=context)
        account = tx.acquirer_id
        reference = tx.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), tx.partner_id.id)

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': long(tx.amount * 100),
            'CURRENCY': tx.currency_id.name,
            'OPERATION': 'SAL',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': tx.payment_method_id.acquirer_ref,
            'RTIMEOUT': 30,
        }

        if kwargs.get('3d_secure'):
            data.update({
                'FLAG3D': 'Y',
                'LANGUAGE': tx.partner_id.lang or 'en_US',
            })

            for url in 'accept decline exception'.split():
                key = '{0}_url'.format(url)
                val = kwargs.pop(key, None)
                if val:
                    key = '{0}URL'.format(url).upper()
                    data[key] = val

        data['SHASIGN'] = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'in', data)

        direct_order_url = 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % (tx.acquirer_id.environment)

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

        return self._ogone_s2s_validate_tree(tx, tree)

    def _ogone_s2s_validate(self, tx):
        tree = self._ogone_s2s_get_tx_status(tx)
        return self._ogone_s2s_validate_tree(tx, tree)

    def _ogone_s2s_validate_tree(self, tx, tree, tries=2):
        if tx.state not in ('draft', 'pending'):
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', tx.reference)
            return True

        status = int(tree.get('STATUS') or 0)
        if status in self._ogone_valid_tx_status:
            tx.write({
                'state': 'done',
                'date_validate': datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': tree.get('PAYID'),
            })
            if tree.get('ALIAS') and tx.partner_id and tx.type == 'form_save' and not tx.payment_method_id:
                pm = tx.env['payment.method'].create({
                    'partner_id': tx.partner_id.id,
                    'acquirer_id': tx.acquirer_id.id,
                    'acquirer_ref': tree.get('ALIAS'),
                    'name': tree.get('CARDNO'),
                })
                tx.write({'payment_method_id': pm.id})
            if tx.callback_eval:
                safe_eval(tx.callback_eval, {'self': tx})
            return True
        elif status in self._ogone_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': tree.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': tree.get('PAYID'),
                'html_3ds': str(tree.HTML_ANSWER).decode('base64')
            })
        elif (not status or status in self._ogone_wait_tx_status) and tries > 0:
            time.sleep(500)
            tx.write({'acquirer_reference': tree.get('PAYID')})
            tree = self._ogone_s2s_get_tx_status(tx)
            return self._ogone_s2s_validate_tree(tx, tree, tries - 1)
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': tree.get('NCERRORPLUS'),
                'error_code': tree.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(tree.get('NCERROR')),
            }
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree.get('PAYID'),
            })
            return False

    def _ogone_s2s_get_tx_status(self, tx):
        account = tx.acquirer_id
        #reference = tx.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), tx.partner_id.id)

        data = {
            'PAYID': tx.acquirer_reference,
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
        }

        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (tx.acquirer_id.environment)

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
