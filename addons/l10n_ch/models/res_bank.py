# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from stdnum.util import clean

from odoo import api, fields, models, _
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.base_iban.models.res_partner_bank import normalize_iban, pretty_iban, validate_iban
from odoo.exceptions import ValidationError
from odoo.tools import LazyTranslate
from odoo.tools.misc import mod10r

_lt = LazyTranslate(__name__)


def validate_qr_iban(qr_iban):
    # Check first if it's a valid IBAN.
    validate_iban(qr_iban)

    # We sanitize first so that _check_qr_iban_range() can extract correct IID from IBAN to validate it.
    sanitized_qr_iban = sanitize_account_number(qr_iban)

    if sanitized_qr_iban[:2] not in ['CH', 'LI']:
        raise ValidationError(_lt("QR-IBAN numbers are only available in Switzerland."))

    # Now, check if it's valid QR-IBAN (based on its IID).
    if not check_qr_iban_range(sanitized_qr_iban):
        raise ValidationError(_lt("QR-IBAN “%s” is invalid.", qr_iban))

    return True

def check_qr_iban_range(iban):
    if not iban or len(iban) < 9:
        return False
    iid_start_index = 4
    iid_end_index = 8
    iid = iban[iid_start_index : iid_end_index+1]
    return re.match(r'\d+', iid) and 30000 <= int(iid) <= 31999 # Those values for iid are reserved for QR-IBANs only


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ch_qr_iban = fields.Char(string='QR-IBAN',
                                  compute='_compute_l10n_ch_qr_iban',
                                  store=True,
                                  readonly=False,
                                  help="Put the QR-IBAN here for your own bank accounts.  That way, you can "
                                       "still use the main IBAN in the Account Number while you will see the "
                                       "QR-IBAN for the barcode.  ")

    # fields to configure payment slip generation
    l10n_ch_display_qr_bank_options = fields.Boolean(compute='_compute_l10n_ch_display_qr_bank_options')

    @api.depends('partner_id', 'company_id')
    def _compute_l10n_ch_display_qr_bank_options(self):
        for bank in self:
            if bank.partner_id:
                bank.l10n_ch_display_qr_bank_options = bank.partner_id.ref_company_ids.country_id.code in ('CH', 'LI')
            elif bank.company_id:
                bank.l10n_ch_display_qr_bank_options = bank.company_id.account_fiscal_country_id.code in ('CH', 'LI')
            else:
                bank.l10n_ch_display_qr_bank_options = self.env.company.account_fiscal_country_id.code in ('CH', 'LI')

    @api.depends('acc_number')
    def _compute_l10n_ch_qr_iban(self):
        for record in self:
            try:
                validate_qr_iban(record.acc_number)
                valid_qr_iban = True
            except ValidationError:
                valid_qr_iban = False
            if valid_qr_iban:
                record.l10n_ch_qr_iban = record.sanitized_acc_number
            else:
                record.l10n_ch_qr_iban = None

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('l10n_ch_qr_iban'):
                validate_qr_iban(vals['l10n_ch_qr_iban'])
                vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('l10n_ch_qr_iban'):
            validate_qr_iban(vals['l10n_ch_qr_iban'])
            vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().write(vals)

    def _l10n_ch_get_qr_vals(self, amount, currency, debtor_partner, free_communication, structured_communication):
        comment = ""
        if free_communication:
            comment = (free_communication[:137] + '...') if len(free_communication) > 140 else free_communication

        creditor_addr_1, creditor_addr_2 = self._get_partner_address_lines(self.partner_id)
        debtor_addr_1, debtor_addr_2 = self._get_partner_address_lines(debtor_partner)

        # Compute reference type (empty by default, only mandatory for QR-IBAN,
        # and must then be 27 characters-long, with mod10r check digit as the 27th one)
        reference_type = 'NON'
        reference = ''
        acc_number = self.sanitized_acc_number

        if self.l10n_ch_qr_iban:
            # _check_for_qr_code_errors ensures we can't have a QR-IBAN without a QR-reference here
            reference_type = 'QRR'
            reference = structured_communication
            acc_number = sanitize_account_number(self.l10n_ch_qr_iban)
        elif self._is_iso11649_reference(structured_communication):
            reference_type = 'SCOR'
            reference = structured_communication.replace(' ', '')

        currency = currency or self.currency_id or self.company_id.currency_id

        return [
            'SPC',                                                # QR Type
            '0200',                                               # Version
            '1',                                                  # Coding Type
            acc_number,                                           # IBAN / QR-IBAN
            'K',                                                  # Creditor Address Type
            (self.acc_holder_name or self.partner_id.name)[:70],  # Creditor Name
            creditor_addr_1,                                      # Creditor Address Line 1
            creditor_addr_2,                                      # Creditor Address Line 2
            '',                                                   # Creditor Postal Code (empty, since we're using combined addres elements)
            '',                                                   # Creditor Town (empty, since we're using combined addres elements)
            self.partner_id.country_id.code,                      # Creditor Country
            '',                                                   # Ultimate Creditor Address Type
            '',                                                   # Name
            '',                                                   # Ultimate Creditor Address Line 1
            '',                                                   # Ultimate Creditor Address Line 2
            '',                                                   # Ultimate Creditor Postal Code
            '',                                                   # Ultimate Creditor Town
            '',                                                   # Ultimate Creditor Country
            '{:.2f}'.format(amount),                              # Amount
            currency.name,                                        # Currency
            'K',                                                  # Ultimate Debtor Address Type
            debtor_partner.commercial_partner_id.name[:70],       # Ultimate Debtor Name
            debtor_addr_1,                                        # Ultimate Debtor Address Line 1
            debtor_addr_2,                                        # Ultimate Debtor Address Line 2
            '',                                                   # Ultimate Debtor Postal Code (not to be provided for address type K)
            '',                                                   # Ultimate Debtor Postal City (not to be provided for address type K)
            debtor_partner.country_id.code,                       # Ultimate Debtor Postal Country
            reference_type,                                       # Reference Type
            reference,                                            # Reference
            comment,                                              # Unstructured Message
            'EPD',                                                # Mandatory trailer part
        ]

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'ch_qr':
            return self._l10n_ch_get_qr_vals(amount, currency, debtor_partner, free_communication, structured_communication)
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'ch_qr':
            return {
                'barcode_type': 'QR',
                'width': 256,
                'height': 256,
                'quiet': 1,
                'mask': 'ch_cross',
                'value': '\n'.join(self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)),
                # Swiss QR code requires Error Correction Level = 'M' by specification
                'barLevel': 'M',
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_partner_address_lines(self, partner):
        """ Returns a tuple of two elements containing the address lines to use
        for this partner. Line 1 contains the street and number, line 2 contains
        zip and city. Those two lines are limited to 70 characters
        """
        streets = [partner.street, partner.street2]
        line_1 = ' '.join(filter(None, streets))
        line_2 = partner.zip + ' ' + partner.city
        return line_1[:70], line_2[:70]

    @api.model
    def _is_qr_reference(self, reference):
        """ Checks whether the given reference is a QR-reference, i.e. it is
        made of 27 digits, the 27th being a mod10r check on the 26 previous ones.
        """
        return reference \
            and len(reference) == 27 \
            and re.match(r'\d+$', reference) \
            and reference == mod10r(reference[:-1])

    @api.model
    def _is_iso11649_reference(self, reference):
        """ Checks whether the given reference is a ISO11649 (SCOR) reference.
        """
        return reference \
               and len(reference) >= 5 \
               and len(reference) <= 25 \
               and reference.startswith('RF') \
               and int(''.join(str(int(x, 36)) for x in clean(reference[4:] + reference[:4], ' -.,/:').upper().strip())) % 97 == 1
               # see https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/iso11649.py

    def _l10n_ch_qr_debtor_check(self, debtor_partner):
        """  This method should be used in _get_error_messages_for_qr and _check_for_qr_code_errors
             It allows is to permit to set this qr method if a partner is not yet provided when executing _get_error_messages_for_qr
             while preventing to print qr code when executing _check_for_qr_code_errors if the partner is not provided
        """
        if not debtor_partner or debtor_partner.country_id.code not in ('CH', 'LI'):
            return _("The debtor partner's address isn't located in Switzerland.")
        return False

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        def _get_error_for_ch_qr():
            error_messages = [_("The Swiss QR code could not be generated for the following reason(s):")]
            if self.acc_type != 'iban':
                error_messages.append(_("The account type isn't QR-IBAN or IBAN."))
            debtor_check = self._l10n_ch_qr_debtor_check(debtor_partner)
            if debtor_partner and debtor_check:
                error_messages.append(debtor_check)
            if currency.id not in (self.env.ref('base.EUR').id, self.env.ref('base.CHF').id):
                error_messages.append(_("The currency isn't EUR nor CHF."))
            return '\r\n'.join(error_messages) if len(error_messages) > 1 else None

        if qr_method == 'ch_qr':
            return _get_error_for_ch_qr()
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        def _partner_fields_set(partner):
            return partner.zip and \
                   partner.city and \
                   partner.country_id.code and \
                   (partner.street or partner.street2)

        if qr_method == 'ch_qr':
            if not _partner_fields_set(self.partner_id):
                return _("The partner set on the bank account meant to receive the payment (%s) must have a complete postal address (street, zip, city and country).", self.acc_number)

            if debtor_partner and not _partner_fields_set(debtor_partner):
                return _("The partner must have a complete postal address (street, zip, city and country).")

            if self.l10n_ch_qr_iban and not self._is_qr_reference(structured_communication):
                return _("When using a QR-IBAN as the destination account of a QR-code, the payment reference must be a QR-reference.")

            debtor_check = self._l10n_ch_qr_debtor_check(debtor_partner)
            if debtor_check:
                return debtor_check

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('ch_qr', _("Swiss QR bill"), 10))
        return rslt
