# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.payment_sepa_direct_debit import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(selection_add=[('sepa_direct_debit', "SEPA Direct Debit")])

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.custom_mode == 'sepa_direct_debit').update({
            'show_credentials_page': False,
            'show_allow_tokenization': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.custom_mode == 'sepa_direct_debit').update({
            'support_tokenization': True,
        })

    #=== CONSTRAINT METHODS ===#

    @api.constrains('state', 'journal_id')
    def _check_journal_iban_is_valid(self):
        """ Check that the bank account of the payment journal is a valid IBAN. """
        for provider in self.filtered(
            lambda p: p.custom_mode == 'sepa_direct_debit' and p.state == 'enabled'
        ):
            if provider.journal_id.bank_account_id.acc_type != 'iban':
                raise ValidationError(_("The bank account of the journal is not a valid IBAN."))

    @api.constrains('state', 'company_id')
    def _check_has_creditor_identifier(self):
        """ Check that the company has a creditor identifier. """
        for provider in self.filtered(
            lambda p: p.custom_mode == 'sepa_direct_debit' and p.state == 'enabled'
        ):
            if not provider.company_id.sdd_creditor_identifier:
                raise ValidationError(_(
                    "Your company must have a creditor identifier in order to issue a SEPA Direct "
                    "Debit payment request. It can be set in Accounting settings."
                ))

    @api.constrains('available_country_ids')
    def _check_country_in_sepa_zone(self):
        """ Check that all selected countries are in the SEPA zone. """
        sepa_countries = self.env.ref('base.sepa_zone').country_ids
        for provider in self.filtered(lambda p: p.custom_mode == 'sepa_direct_debit'):
            non_sepa_countries = provider.available_country_ids - sepa_countries
            if non_sepa_countries:
                raise ValidationError(_(
                    "Restricted to countries in the SEPA zone. Forbidden countries: %s",
                    ', '.join(non_sepa_countries.mapped('name'))
                ))

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of `payment` to unlist SDD providers for validation flows.

        Tokens are created automatically once the direct transaction is confirmed, but cannot be
        created through validation flows.
        """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'sepa_direct_debit'
            )

        return providers

    def _get_supported_currencies(self):
        """ Override of `payment` to return EUR as the only supported currency. """
        supported_currencies = super()._get_supported_currencies()
        if self.custom_mode == 'sepa_direct_debit':
            supported_currencies = supported_currencies.filtered(lambda c: c.name == 'EUR')
        return supported_currencies

    def _is_tokenization_required(self, **kwargs):
        """ Override of payment to hide the "Save my payment details" input in checkout forms.

        :return: Whether the provider is SEPA
        :rtype: bool
        """
        res = super()._is_tokenization_required(**kwargs)
        if len(self) != 1 or self.custom_mode != 'sepa_direct_debit':
            return res

        return True

    def _sdd_find_or_create_mandate(self, partner_id, iban):
        """ Find or create the SDD mandate verified by the given phone.

        Note: self.ensure_one()

        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The sanitized IBAN number of the partner's bank account
        :return: The SDD mandate
        :rtype: recordset of `sdd.mandate`
        """
        self.ensure_one()

        commercial_partner_id = self.env['res.partner'].browse(partner_id).commercial_partner_id.id
        partner_bank = self._sdd_find_or_create_partner_bank(partner_id, iban)
        mandate = self.env['sdd.mandate'].search([
            ('state', 'not in', ['closed', 'revoked']),
            ('start_date', '<=', datetime.now()),
            '|', ('end_date', '>=', datetime.now()), ('end_date', '=', None),
            ('partner_id', '=', commercial_partner_id),
            ('partner_bank_id', '=', partner_bank.id),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not mandate:
            mandate = self.env['sdd.mandate'].create({
                'partner_id': commercial_partner_id,
                'partner_bank_id': partner_bank.id,
                'start_date': datetime.now(),
                'payment_journal_id': self.journal_id.id,
                'state': 'draft',
            })
        return mandate

    def _sdd_find_or_create_partner_bank(self, partner_id, iban):
        """ Find or create the partner bank with the given iban.

        Note: self.ensure_one()

        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The sanitized IBAN number of the partner's bank account
        :return: The partner bank
        :rtype: recordset of `res.partner.bank`
        """
        self.ensure_one()

        ResPartnerBank = self.env['res.partner.bank']
        commercial_partner_id = self.env['res.partner'].browse(partner_id).commercial_partner_id.id
        partner_bank = ResPartnerBank.search([
            ('sanitized_acc_number', '=', iban),
            ('partner_id', 'child_of', commercial_partner_id),
        ])
        if not partner_bank:
            partner_bank = ResPartnerBank.create({
                'acc_number': iban,
                'partner_id': partner_id,
                'company_id': self.company_id.id,
            })
        return partner_bank

    def _sdd_create_token_for_mandate(self, partner, mandate):
        """ Create a token linked to the mandate with the obfuscated IBAN as name and return it.

        :param res.partner partner: The partner making the transaction.
        :param sdd.mandate mandate: The mandate to link to the token.
        :return: The created token.
        :rtype: payment.token
        :raise AccessError: If the partner is different than the mandate's partner.
        """
        # Since we're in a sudoed env, we need to verify the partner
        if mandate.partner_id != partner.commercial_partner_id:
            raise AccessError("SEPA: " + _("The mandate owner and customer do not match."))

        return self.env['payment.token'].create({
            'provider_id': self.id,
            'payment_method_id': self.payment_method_ids[:1].id,
            'payment_details': mandate.partner_bank_id.acc_number,
            'partner_id': partner.id,
            'provider_ref': mandate.name,
            'sdd_mandate_id': mandate.id,
        })

    def _get_provider_name(self):
        """ Override of `payment` to display "Managed by SEPA" instead of "Managed by Custom" on the
        payment form. """
        if self.code != 'custom' or self.custom_mode != 'sepa_direct_debit':
            return super()._get_provider_name()
        return dict(self._fields['custom_mode']._description_selection(self.env))[self.custom_mode]

    def _get_code(self):
        """ Override of `payment` to trick the JS into believing the code is 'sepa_direct_debit'.
        """
        res = super()._get_code()
        if self.code == 'custom' and self.custom_mode == 'sepa_direct_debit':
            return self.custom_mode
        return res

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.custom_mode != 'sepa_direct_debit':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
