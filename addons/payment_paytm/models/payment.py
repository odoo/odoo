# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paytm.models import paytm_utils
from odoo.addons.payment_paytm.controllers.main import PaytmController

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paytm', 'Paytm')])
    paytm_merchant_id = fields.Char(
        string='Paytm Merchant ID', required_if_provider='paytm', groups='base.group_user')
    paytm_merchant_key = fields.Char(
        string='Paytm Merchant Key', required_if_provider='paytm', groups='base.group_user')
    paytm_industry_type = fields.Char(
        string='Industry Type', required_if_provider='paytm', groups='base.group_user')
    paytm_website = fields.Char(
        string='Paytm Website', required_if_provider='paytm', groups='base.group_user')

    def _get_paytm_urls(self, environment):
        """ Paytm URLs"""
        if environment == 'prod':
            return {'paytm_form_url': 'https://securegw.paytm.in/theia/processTransaction'}
        return {'paytm_form_url': 'https://securegw-stage.paytm.in/theia/processTransaction'}

    @api.multi
    def paytm_form_generate_values(self, values):
        self.ensure_one()
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        if currency != self.env.ref('base.INR'):
            raise ValidationError(_('Currency not supported by Paytm'))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        paytm_values = dict(MID=self.paytm_merchant_id,
                            ORDER_ID=values.get('reference'),
                            CUST_ID=values.get('partner').id,
                            TXN_AMOUNT=values.get('amount'),
                            CHANNEL_ID='WEB',
                            WEBSITE=self.paytm_website,
                            MOBILE_NO=values.get('partner_phone'),
                            EMAIL=values.get('partner_email'),
                            INDUSTRY_TYPE_ID=self.paytm_industry_type,
                            CALLBACK_URL=urls.url_join(base_url, PaytmController._callback_url),
                            )
        paytm_values['CHECKSUMHASH'] = paytm_utils.generate_checksum(paytm_values, self.paytm_merchant_key)
        values.update(paytm_values)
        return values

    @api.multi
    def paytm_get_form_action_url(self):
        self.ensure_one()
        return self._get_paytm_urls(self.environment)['paytm_form_url']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, values=None, prefix=None):
        res = super(PaymentTransaction, self)._compute_reference(values=values, prefix=prefix)
        acquirer = self.env['payment.acquirer'].browse(values.get('acquirer_id'))
        if acquirer and acquirer.provider == 'paytm':
            return re.sub(r"[^\w@_.-]+", '', res)
        return res

    @api.model
    def _paytm_form_get_tx_from_data(self, data):
        """ Given a data dict coming from Paytm, verify it and find the related
            transaction record. """
        reference = data.get('ORDERID')
        if not reference:
            raise ValidationError(_('Paytm: received data with missing reference (%s)') % (reference))
        transaction = self.search([('reference', '=', reference)])
        if not transaction or len(transaction) > 1:
            error_msg = _('Paytm: received data for reference %s') % (reference)
            if not transaction:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            raise ValidationError(error_msg)
        return transaction

    @api.model
    def _paytm_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # check what is buyed
        if float_compare(float(data.get('TXNAMOUNT', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('TXNAMOUNT', data.get('TXNAMOUNT'), '%.2f' % self.amount))
        if data.get('MID') and self.acquirer_id.paytm_merchant_id and data['MID'] != self.acquirer_id.paytm_merchant_id:
            invalid_parameters.append(('MID', data.get('MID'), self.acquirer_id.paytm_merchant_id))

        CHECKSUMHASH = data.get('CHECKSUMHASH')
        verify_checksum = paytm_utils.verify_checksum(data, self.acquirer_id.paytm_merchant_key, CHECKSUMHASH).decode()
        if not CHECKSUMHASH or CHECKSUMHASH != verify_checksum:
            invalid_parameters.append(('CHECKSUMHASH', verify_checksum, CHECKSUMHASH))

        return invalid_parameters

    @api.model
    def _paytm_form_validate(self, data):
        if self.state == 'done':
            _logger.warning('Paytm: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = data.get('STATUS')
        if status_code == 'TXN_SUCCESS':
            _logger.info('Validated Paytm payment for tx %s: set as done' % (self.reference))
            self.write({'acquirer_reference': data.get('TXNID'), 'state_message': data.get('RESPMSG')})
            self._set_transaction_done()
            return True
        elif status_code == 'PENDING':
            _logger.info('Received notification for Paytm payment %s: set as pending' % (self.reference))
            self.write({'acquirer_reference': data.get('TXNID'), 'state_message': data.get('RESPMSG')})
            self._set_transaction_pending()
            return False
        else:
            error = data.get('RESPMSG') or data.get('status_message')
            _logger.info(error)
            self.write({'acquirer_reference': data.get('TXNID'), 'state_message': error})
            self._set_transaction_error(error)
            return False
