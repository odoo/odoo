# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .paymob_pos_request import (
    PAYMOB_PRODUCTION_URLS,
    PAYMOB_STAGING_URL,
    PaymobPosRequest,
)

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    _paymob_terminal_unique = models.Constraint(
        'unique(paymob_terminal_identifier)',
        'This Paymob terminal is already used on another payment method.',
    )

    paymob_api_key = fields.Char(
        string="Paymob API Key",
        help="The API key from your Paymob dashboard (Profile tab), used to authenticate with Paymob.",
        copy=False, groups='base.group_erp_manager')
    paymob_terminal_identifier = fields.Char(
        string="Paymob Terminal ID",
        help="The ID of the Paymob terminal the payment notification is pushed to.",
        copy=False)
    paymob_hmac_secret = fields.Char(
        string="Paymob HMAC Secret",
        help="The HMAC secret from your Paymob dashboard, required to verify callbacks. "
             "Without it, Paymob payment callbacks are rejected.",
        copy=False, groups='base.group_erp_manager')
    paymob_test_mode = fields.Boolean(
        string="Paymob Test Mode",
        help="Run transactions in the Paymob staging environment.",
        groups='base.group_erp_manager')
    paymob_latest_response = fields.Char(
        copy=False, groups='base.group_erp_manager')  # buffers the latest verified callback
    paymob_callback_url = fields.Char(
        string="Paymob Callback URL",
        help="Set this as the transaction callback URL in your Paymob dashboard so Paymob can notify Odoo of the result.",
        compute='_compute_paymob_callback_url')

    def _compute_paymob_callback_url(self):
        base_url = self.get_base_url()
        for payment_method in self:
            payment_method.paymob_callback_url = base_url + '/pos_paymob/notification'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('paymob', 'Paymob')]

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['paymob_terminal_identifier']
        return params

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'paymob_latest_response'})

    def _check_special_access(self):
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You do not have access to communicate with Paymob."))

    def _get_paymob_base_url(self):
        self.ensure_one()
        if self.sudo().paymob_test_mode:
            return PAYMOB_STAGING_URL
        country_code = self.company_id.country_id.code or self.env.company.country_id.code
        base_url = PAYMOB_PRODUCTION_URLS.get(country_code)
        if not base_url:
            raise UserError(_(
                "Paymob is not available for your company's country (%s). Supported countries: Egypt, United Arab Emirates.",
                country_code or _("not set")))
        return base_url

    def _paymob_make_request(self):
        self.ensure_one()
        return PaymobPosRequest(self.sudo().paymob_api_key, self._get_paymob_base_url())

    def paymob_create_order(self, infos):
        """ Register an order at Paymob and push a pay notification to the terminal.
        ``infos`` carries the amount, currency and the ``merchant_order_id`` the
        callback is routed back on. """
        self.ensure_one()
        self._check_special_access()
        # Clear any stale response so we don't process an old callback.
        self.sudo().paymob_latest_response = ''
        terminal_id = self.sudo().paymob_terminal_identifier
        payload = {
            **infos,
            'terminal_id': terminal_id,
            'send_pay_notification_to_terminal_id': terminal_id,
            'preferred_payment_method': 'card',
            'transaction_type': 'sale',
            'delivery_needed': 'false',
        }
        response = self._paymob_make_request().create_order(payload)
        _logger.debug("paymob_create_order response: %s", response)
        return response

    def paymob_send_reversal(self, infos):
        """ Reverse a past Paymob transaction on the same terminal; the result arrives
        over the callback. ``infos`` carries the original sale's ``transaction_id``,
        ``amount_cents`` and ``currency``.

        A not-yet-settled transaction reversed in full is voided (cancels the
        authorisation); a settled transaction or a partial reversal is refunded,
        since Paymob only voids the full amount. """
        self.ensure_one()
        self._check_special_access()
        # Clear any stale response so we don't process an old callback.
        self.sudo().paymob_latest_response = ''
        request = self._paymob_make_request()
        payload = {
            **infos,
            'send_pay_notification_to_terminal_id': self.sudo().paymob_terminal_identifier,
            'preferred_payment_method': 'card',
        }
        # On a failed inquiry, default to a refund (the safer, partial-capable path).
        inquiry = request.get_transaction(infos.get('transaction_id'))
        settled = not isinstance(inquiry, dict) or inquiry.get('is_settled')
        full_amount = isinstance(inquiry, dict) and infos.get('amount_cents') == inquiry.get('amount_cents')
        if not settled and full_amount:
            response = request.send_void(payload)
        else:
            response = request.send_refund(payload)
        _logger.debug("paymob_send_reversal response: %s", response)
        return response

    def paymob_get_payment_status(self, criteria):
        """ Fetch the callback result buffered by the controller, if every field in
        ``criteria`` matches it. """
        self.ensure_one()
        self._check_special_access()
        latest_response = self.sudo().paymob_latest_response
        latest_response = json.loads(latest_response) if latest_response else False
        if not latest_response:
            return False
        if all(latest_response.get(key) == value for key, value in criteria.items()):
            return latest_response
        return False
