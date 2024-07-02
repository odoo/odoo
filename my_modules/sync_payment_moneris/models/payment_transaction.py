# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment import utils as payment_utils

from . import moneris_request

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    _moneris_valid_tx_status = 27

    cust_id = fields.Char('Customer ID')
    receipt_id = fields.Char('Receipt ID')
    response_code = fields.Char('Response Code')
    cc_number = fields.Char('Credit Card')
    expdate = fields.Char('Expiry Date')
    cardtype = fields.Char('Card Type')
    trans_time = fields.Char('Transaction Time')
    trans_date = fields.Char('Transaction Date')
    payment_type = fields.Char('Payment Type')
    reference_num = fields.Char('Reference Number')
    bank_approval_code = fields.Char('Bank Approval Code')
    trans_id = fields.Char('Transaction ID')
    # Capture Fields
    capture_reference_num = fields.Char('Capture Reference Number')
    capture_trans_date = fields.Char('Capture Transaction Time')
    capture_trans_time = fields.Char('Capture Transaction Date')
    # Void Fields
    void_reference_num = fields.Char('Void Reference Number')
    void_trans_date = fields.Char('Void Transaction Time')
    void_trans_time = fields.Char('Void Transaction Date')

    #=== BUSINESS METHODS ===#

    def action_void(self):
        """ Check the state of the transaction and request to have them voided. """
        for tx in self:
            if tx.provider_code != 'moneris':
                tx_records = super(PaymentTransaction, tx).action_void()

            payment_utils.check_rights_on_recordset(tx)
            # In sudo mode because we need to be able to read on provider fields.
            if tx.state == 'done':
                tx.sudo()._send_void_request()

    def _get_model_id(self):
        model_id = False
        reference = self.reference.split('-')
        if 'x' in self.reference:
            reference = self.reference.split('x')
        if reference:
            model_id = self.env['account.move'].sudo().search([('name', '=', reference[0])], limit=1)
            if not model_id:
                model_id = self.env['sale.order'].sudo().search([('name', '=', reference[0])], limit=1)
        return model_id

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Authorize.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'moneris':
            return

        if not self.token_id:
            raise UserError("Moneris Checkout: " + _("The transaction is not linked to a token."))

        if self.provider_id.capture_manually:
            authorize_req = moneris_request.MonerisAuthorizeRequest(store_id=self.provider_id.store_id,
                                api_token=self.provider_id.api_token,
                                data_key=self.token_id.provider_ref,
                                order_id=self.reference, amount=self.amount,
                                customer_id=self.partner_id.customer_id, provider_id=self.provider_id)
            response = authorize_req.send()
            _logger.info(
                "Authorize request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(response)
            )
        else:
            country = self.partner_country_id and self.partner_country_id.name or '',
            state = self.partner_state_id and self.partner_state_id.name or '',
            is_invoice_payment, is_sale_payment, order_lines = False, False, False
            model_id = self._get_model_id()
            if model_id._name == 'sale.order':
                is_sale_payment = True
                order_lines = model_id.order_line.filtered(lambda x: x.product_id or x.price_subtotal == 0)
            elif model_id._name == 'account.move':
                is_invoice_payment = True
                order_lines = model_id.invoice_line_ids.filtered(lambda x: x.product_id or x.price_subtotal == 0)
            purchase_req = moneris_request.MonerisPurchaseRequest(store_id=self.provider_id.store_id,
                                api_token=self.provider_id.api_token,
                                data_key=self.token_id.provider_ref,
                                order_id=self.reference, customer_id=self.partner_id.customer_id,
                                amount=self.amount,
                                email=self.partner_email, first_name=self.partner_name,
                                street=self.partner_address, city=self.partner_city,
                                state=state, zip=self.partner_zip, country=country,
                                phone_number=self.partner_phone, order_lines=order_lines, trxn_type='res_purchase_cc',
                                provider_id=self.provider_id, is_invoice_payment=is_invoice_payment, is_sale_payment=is_sale_payment)
            response = purchase_req.send()
            _logger.info(
                "Auth and Capture request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(response)
            )
        self._handle_notification_data('moneris', response)

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != 'moneris':
            return

        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        capture_req = moneris_request.MonerisCaptureRequest(store_id=self.provider_id.store_id, \
                            api_token=self.provider_id.api_token, order_id=self.reference, \
                            comp_amount=rounded_amount, txn_number=self.trans_id, \
                            provider_id=self.provider_id)
        response = capture_req.send()
        _logger.info(
            "Moneris: Capture request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response)
        )
        self._handle_notification_data('moneris', response)

    def _send_void_request(self):
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'moneris':
            return

        void_req = moneris_request.MonerisVoidRequest(store_id=self.provider_id.store_id, api_token=self.provider_id.api_token,
                                                          order_id=self.reference, txn_number=self.trans_id, provider_id=self.provider_id)
        response = void_req.send()
        _logger.info(
            "Moneris: Void request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response)
        )
        self._handle_notification_data('moneris', response)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Alipay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'moneris' or len(tx) == 1:
            return tx

        response = notification_data.get('response', {}) or {}
        status = response.get('success')
        request = response.get('request', {}) or {}
        receipt = response.get('receipt', {}) or {}
        result = receipt.get('result')
        reference = request.get('order_no')

        if not reference:
            raise ValidationError(
                "Moneris: " + _(
                    "Received data with missing reference %(r)s.",
                    r=reference
                )
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'moneris')])
        if not tx:
            raise ValidationError(
                "Moneris: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _set_canceled(self, state_message=None, extra_allowed_states=()):
        
        if self.provider_id.code != "moneris":
            return super()._set_canceled(state_message=state_message, extra_allowed_states=extra_allowed_states)

        allowed_states = ('done', 'draft', 'pending', 'authorized')
        target_state = 'cancel'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._update_source_transaction_state()
        txs_to_process._log_received_message()
        return txs_to_process

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Alipay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'moneris':
            return

        if self.state == 'done' and 'trans_type' in notification_data and notification_data.get('trans_type') != '11':
            _logger.warning('Moneris: trying to validate an already validated tx (ref %s)' % self.reference)
            return True

        if 'api_request' in notification_data:

            if 'error' in notification_data:
                tx_type = notification_data.get('tx_type')
                message = notification_data.get('message')
                state_message = "Moneris: Received response for transaction with reference %s:\nMessage: %s" % (self.reference, message)
                self._set_error(state_message)
            else:
                response_code, flag = notification_data.get('response_code') or '', True
                if response_code == 'none':
                    response_code = ''
                try:
                    response_code = int(response_code)
                except ValueError:
                    flag = False

                message = notification_data.get('message') or ''
                complete = notification_data.get('complete')
                reference_num = notification_data.get('reference_num') or ''
                capture_reference_num = notification_data.get('reference_num') or ''
                trans_date = notification_data.get('trans_date')
                trans_time = notification_data.get('trans_time')

                cc_number = notification_data.get('cc_number')
                cardtype = notification_data.get('cardtype')
                payment_type = notification_data.get('payment_type')
                expdate = notification_data.get('expdate')
                trans_type = notification_data.get('trans_type')
                trans_id = notification_data.get('trans_id')

                state_message = "Moneris: Response for transaction with reference %s:\nCode: %s \nMessage: %s" % (self.reference, str(response_code), message)
                tx_vals = {
                    'provider_reference': reference_num,
                    'response_code': response_code,
                    'cc_number': cc_number,
                    'expdate': expdate,
                    'cardtype': cardtype,
                    'trans_date': trans_date,
                    'trans_time': trans_time,
                    'trans_id': trans_id,
                    'state_message': state_message
                }
                self.write(tx_vals)
                if isinstance(response_code, int) and response_code < 50:
                    if trans_type == '00':  # Purchase request
                        self._set_done()
                    elif trans_type == '01': # Preauthorize request
                        self._set_authorized()
                    elif trans_type == '02': # Capture request
                        tx_vals = {
                            'capture_reference_num': capture_reference_num,
                            'capture_trans_date': trans_date,
                            'capture_trans_time': trans_time
                        }
                        self.write(tx_vals)
                        self._set_done()
                    elif trans_type == '11': # Decline
                        tx_vals = {
                            'void_reference_num': capture_reference_num,
                            'void_trans_date': trans_date,
                            'void_trans_time': trans_time
                        }
                        self.write(tx_vals)
                        self._set_canceled(state_message)
                else:
                    self._set_error(state_message)
        else:
            response = notification_data.get('response', {}) or {}
            save_token = notification_data.get('save_token', False)
            receipt = response.get('receipt', {}) or {}
            cc = receipt.get('cc', {}) or {}
            tokenize = cc.get('tokenize', {}) or {}
            message = cc.get('message', '')
            response_code, flag = cc.get('response_code'), True

            if response_code is None:
                response_code = ''
            try:
                response_code = int(response_code)
            except ValueError:
                flag = False

            if save_token and tokenize.get('success') == 'true':
                token = self.env['payment.token'].create({
                    'provider_id': self.provider_id.id,
                    'payment_details': tokenize.get('first4last4'),
                    'partner_id': self.partner_id.id,
                    'provider_ref': tokenize.get('datakey'),
                    'payment_method_id': self.env.ref("payment.payment_method_card").id,
                })
                self.write({
                    'token_id': token,
                    'tokenize': False,
                })
                _logger.info(
                    "created token with id %(token_id)s for partner with id %(partner_id)s from "
                    "transaction with reference %(ref)s",
                    {
                        'token_id': token.id,
                        'partner_id': self.partner_id.id,
                        'ref': self.reference,
                    },
                )

            tx_vals = {
                'provider_reference': cc.get('reference_no', ''),
                'response_code': response_code,
                'cc_number': cc.get('first6last4', ''),
                'expdate': cc.get('expiry_date', ''),
                'cardtype': cc.get('card_type', ''),
                'trans_date': cc.get('transaction_date_time', ''),
                'trans_id': cc.get('transaction_no', ''),
                'bank_approval_code': cc.get('approval_code', ''),
            }
            self.write(tx_vals)

            if response.get('success') == 'true' and receipt.get('result') == 'a' and \
                isinstance(response_code, int) and response_code < 50:
                # Success
                if cc.get('transaction_code') == '00':
                    # Purchase
                    self._set_done()
                elif cc.get('transaction_code') == '01':
                    # Pre-Authorization
                    self._set_authorized()
                elif cc.get('transaction_code') == '02':
                    # Capture Tx
                    self._set_done()
            elif response.get('success') == 'false' or response.get('error') or receipt.get('result') == 'b' or \
                (isinstance(response_code, int) and response_code >= 50 or response_code in ['null', 'NULL']):
                # Failed
                error_message = _('Moneris: Received transaction with error code: %s and message: %s' % (response_code, message))
                if response.get('error'):
                    error_message = response.get('error', {}).get('message', '')
                self._set_error("Moneris Error: " + _("%s", error_message))
