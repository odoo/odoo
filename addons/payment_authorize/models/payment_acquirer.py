# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError

from .authorize_request import AuthorizeAPI

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
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
    # Authorize.Net supports only one currency: "One gateway account is required for each currency"
    # See https://community.developer.authorize.net/t5/The-Authorize-Net-Developer-Blog/Authorize-Net-UK-Europe-Update/ba-p/35957
    authorize_currency_id = fields.Many2one(
        string="Authorize Currency", comodel_name='res.currency', groups='base.group_system')
    authorize_payment_method_type = fields.Selection(
        string="Allow Payments From",
        help="Determines with what payment method the customer can pay.",
        selection=[('credit_card', "Credit Card"), ('bank_account', "Bank Account (USA Only)")],
        default='credit_card',
        required_if_provider='authorize',
    )

    @api.constrains('authorize_payment_method_type')
    def _check_payment_method_type(self):
        for acquirer in self.filtered(lambda acq: acq.provider == "authorize"):
            if self.env['payment.token'].search([('acquirer_id', '=', acquirer.id)], limit=1):
                raise ValidationError(_(
                    "There are active tokens linked to this acquirer. To change the payment method "
                    "type, please disable the acquirer and duplicate it. Then, change the payment "
                    "method type on the duplicated acquirer."
                ))

    @api.onchange('authorize_payment_method_type')
    def _onchange_authorize_payment_method_type(self):
        if self.authorize_payment_method_type == 'bank_account':
            self.display_as = _("Bank (powered by Authorize)")
            self.payment_icon_ids = [Command.clear()]
        else:
            self.display_as = _("Credit Card (powered by Authorize)")
            self.payment_icon_ids = [Command.set([self.env.ref(icon_xml_id).id for icon_xml_id in (
                'payment.payment_icon_cc_maestro',
                'payment.payment_icon_cc_mastercard',
                'payment.payment_icon_cc_discover',
                'payment.payment_icon_cc_diners_club_intl',
                'payment.payment_icon_cc_jcb',
                'payment.payment_icon_cc_visa',
            )])]

    def action_update_merchant_details(self):
        """ Fetch the merchant details to update the client key and the account currency. """
        self.ensure_one()

        if self.state == 'disabled':
            raise UserError(_("This action cannot be performed while the acquirer is disabled."))

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
        self.authorize_currency_id = currency
        self.authorize_client_key = res_content.get('publicClientKey')

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Authorize acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency:
            acquirers = acquirers.filtered(
                lambda a: a.provider != 'authorize' or currency == a.authorize_currency_id
            )

        return acquirers

    def _get_validation_amount(self):
        """ Override of payment to return the amount for Authorize.Net validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.provider != 'authorize':
            return res

        return 0.01

    def _get_validation_currency(self):
        """ Override of payment to return the currency for Authorize.Net validation operations.

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        res = super()._get_validation_currency()
        if self.provider != 'authorize':
            return res

        return self.authorize_currency_id

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'authorize':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_authorize.payment_method_authorize').id
