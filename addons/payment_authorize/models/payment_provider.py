# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError

from .authorize_request import AuthorizeAPI

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('authorize', 'Authorize.Net')], ondelete={'authorize': 'set default'})
    authorize_login = fields.Char(
        string="API Login ID", help="The ID solely used to identify the account with Authorize.Net",
        required_if_provider='authorize')
    authorize_transaction_key = fields.Char(
        string="API Transaction Key", required_if_provider='authorize', groups='base.group_system')
    authorize_signature_key = fields.Char(
        string="API Signature Key", required_if_provider='authorize', groups='base.group_system')
    authorize_client_key = fields.Char(
        string="API Client Key",
        help="The public client key. To generate directly from Odoo or from Authorize.Net backend.")
    authorize_payment_method_type = fields.Selection(
        string="Allow Payments From",
        help="Determines with what payment method the customer can pay.",
        selection=[('credit_card', "Credit Card"), ('bank_account', "Bank Account (USA Only)")],
        default='credit_card',
        required_if_provider='authorize',
    )

    # === CONSTRAINT METHODS ===#

    @api.constrains('authorize_payment_method_type')
    def _check_payment_method_type(self):
        for provider in self.filtered(lambda p: p.code == "authorize"):
            if self.env['payment.token'].search([('provider_id', '=', provider.id)], limit=1):
                raise ValidationError(_(
                    "There are active tokens linked to this provider. To change the payment method "
                    "type, please disable the provider and duplicate it. Then, change the payment "
                    "method type on the duplicated provider."
                ))

    # Authorize.Net supports only one currency: "One gateway account is required for each currency"
    # See https://community.developer.authorize.net/t5/The-Authorize-Net-Developer-Blog/Authorize-Net-UK-Europe-Update/ba-p/35957
    @api.constrains('available_currency_ids', 'state')
    def _limit_available_currency_ids(self):
        for provider in self.filtered(lambda p: p.code == 'authorize'):
            if len(provider.available_currency_ids) > 1 and provider.state != 'disabled':
                raise ValidationError(
                    _("Only one currency can be selected by Authorize.Net account.")
                )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'authorize').update({
            'support_manual_capture': True,
            'support_refund': 'full_only',
            'support_tokenization': True,
        })

    # === ONCHANGE METHODS ===#

    @api.onchange('authorize_payment_method_type')
    def _onchange_authorize_payment_method_type(self):
        if self.authorize_payment_method_type == 'bank_account':
            self.display_as = _("Bank (powered by Authorize)")
            self.payment_method_ids = [Command.clear()]
        else:
            self.display_as = _("Credit Card (powered by Authorize)")
            self.payment_method_ids = [Command.set([self.env.ref(pm_xml_id).id for pm_xml_id in (
                'payment.payment_method_maestro',
                'payment.payment_method_mastercard',
                'payment.payment_method_discover',
                'payment.payment_method_diners_club_intl',
                'payment.payment_method_jcb',
                'payment.payment_method_visa',
            )])]

    # === ACTION METHODS ===#

    def action_update_merchant_details(self):
        """ Fetch the merchant details to update the client key and the account currency. """
        self.ensure_one()

        if self.state == 'disabled':
            raise UserError(_("This action cannot be performed while the provider is disabled."))

        authorize_API = AuthorizeAPI(self)

        # Validate the API Login ID and Transaction Key
        res_content = authorize_API.test_authenticate()
        _logger.info("test_authenticate request response:\n%s", pprint.pformat(res_content))
        if res_content.get('err_msg'):
            raise UserError(_("Failed to authenticate.\n%s", res_content['err_msg']))

        # Update the merchant details
        res_content = authorize_API.merchant_details()
        _logger.info("merchant_details request response:\n%s", pprint.pformat(res_content))
        if res_content.get('err_msg'):
            raise UserError(_("Could not fetch merchant details:\n%s", res_content['err_msg']))

        currency = self.env['res.currency'].search([('name', 'in', res_content.get('currencies'))])
        self.available_currency_ids = [Command.set(currency.ids)]
        self.authorize_client_key = res_content.get('publicClientKey')

    # === BUSINESS METHODS ===#

    def _get_validation_amount(self):
        """ Override of payment to return the amount for Authorize.Net validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'authorize':
            return res

        return 0.01

    def _get_validation_currency(self):
        """ Override of payment to return the currency for Authorize.Net validation operations.

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        res = super()._get_validation_currency()
        if self.code != 'authorize':
            return res

        return self.available_currency_ids[0]
