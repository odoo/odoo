# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import werkzeug

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)
TIMEOUT = 10

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('stripe', 'Stripe')]

    # Stripe
    stripe_serial_number = fields.Char(help='[Serial number of the stripe terminal], for example: WSC513105011295', copy=False)

    @api.constrains('stripe_serial_number')
    def _check_stripe_serial_number(self):
        for payment_method in self:
            if not payment_method.stripe_serial_number:
                continue
            existing_payment_method = self.search([('id', '!=', payment_method.id),
                                                   ('stripe_serial_number', '=', payment_method.stripe_serial_number)],
                                                  limit=1)
            if existing_payment_method:
                raise ValidationError(_('Terminal %s is already used on payment method %s.',\
                     payment_method.stripe_serial_number, existing_payment_method.display_name))

    def _get_stripe_payment_provider(self):
        stripe_payment_provider = self.env['payment.provider'].search([('code', '=', 'stripe')], limit=1)

        if not stripe_payment_provider:
            raise UserError(_("Stripe payment provider is missing"))

        return stripe_payment_provider

    @api.model
    def _get_stripe_secret_key(self):
        stripe_secret_key = self._get_stripe_payment_provider().stripe_secret_key

        if not stripe_secret_key:
            raise ValidationError(_('Complete the Stripe onboarding.'))

        return stripe_secret_key

    @api.model
    def stripe_connection_token(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Stripe"))

        endpoint = 'https://api.stripe.com/v1/terminal/connection_tokens'

        try:
            resp = requests.post(endpoint, auth=(self.sudo()._get_stripe_secret_key(), ''), timeout=TIMEOUT)
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call stripe_connection_token endpoint")
            raise UserError(_("There are some issues between us and Stripe, try again later."))

        return resp.json()

    def _stripe_calculate_amount(self, amount):
        currency = self.journal_id.currency_id or self.company_id.currency_id
        return round(amount/currency.rounding)

    def stripe_payment_intent(self, amount):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Stripe"))

        # For Terminal payments, the 'payment_method_types' parameter must include
        # at least 'card_present' and the 'capture_method' must be set to 'manual'.
        endpoint = 'https://api.stripe.com/v1/payment_intents'
        currency = self.journal_id.currency_id or self.company_id.currency_id

        params = [
            ("currency", currency.name),
            ("amount", self._stripe_calculate_amount(amount)),
            ("payment_method_types[]", "card_present"),
            ("capture_method", "manual"),
        ]

        if currency.name == 'CAD' and self.company_id.country_code == 'CA':
            params.append(("payment_method_types[]", "interac_present"))

        try:
            data = werkzeug.urls.url_encode(params)
            resp = requests.post(endpoint, data=data, auth=(self.sudo()._get_stripe_secret_key(), ''), timeout=TIMEOUT)
        except requests.exceptions.RequestException:
            _logger.exception("Failed to call stripe_payment_intent endpoint")
            raise UserError(_("There are some issues between us and Stripe, try again later."))

        return resp.json()

    @api.model
    def stripe_capture_payment(self, paymentIntentId, amount=None):
        """Captures the payment identified by paymentIntentId.

        :param paymentIntentId: the id of the payment to capture
        :param amount: without this parameter the entire authorized
                       amount is captured. Specifying a larger amount allows
                       overcapturing to support tips.
        """
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Stripe"))

        endpoint = ('payment_intents/%s/capture') % (werkzeug.urls.url_quote(paymentIntentId))

        data = None
        if amount is not None:
            data = {
                "amount_to_capture": self._stripe_calculate_amount(amount),
            }

        return self.sudo()._get_stripe_payment_provider()._stripe_make_request(endpoint, data)

    def action_stripe_key(self):
        res_id = self._get_stripe_payment_provider().id
        # Redirect
        return {
            'name': _('Stripe'),
            'res_model': 'payment.provider',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
        }
