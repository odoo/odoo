# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import mod10r

import werkzeug.urls

ISR_SUBSCRIPTION_CODE = {'CHF': '01', 'EUR': '03'}
CLEARING = "09000"
_re_postal = re.compile('^[0-9]{2}-[0-9]{1,6}-[0-9]$')


def _is_l10n_ch_postal(account_ref):
    """ Returns True if the string account_ref is a valid postal account number,
    i.e. it only contains ciphers and is last cipher is the result of a recursive
    modulo 10 operation ran over the rest of it. Shorten form with - is also accepted.
    """
    if _re_postal.match(account_ref or ''):
        ref_subparts = account_ref.split('-')
        account_ref = ref_subparts[0] + ref_subparts[1].rjust(6, '0') + ref_subparts[2]

    if re.match('\d+$', account_ref or ''):
        account_ref_without_check = account_ref[:-1]
        return mod10r(account_ref_without_check) == account_ref
    return False

def _is_l10n_ch_isr_issuer(account_ref, currency_code):
    """ Returns True if the string account_ref is a valid a valid ISR issuer
    An ISR issuer is postal account number that starts by 01 (CHF) or 03 (EUR),
    """
    if (account_ref or '').startswith(ISR_SUBSCRIPTION_CODE[currency_code]):
        return _is_l10n_ch_postal(account_ref)
    return False


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ch_postal = fields.Char(string='Swiss Postal Account', help='This field is used for the Swiss postal account number '
                                                                     'on a vendor account and for the client number on your '
                                                                     'own account.  The client number is mostly 6 numbers without '
                                                                     '-, while the postal account number can be e.g. 01-162-8')
    # fields to configure ISR payment slip generation
    l10n_ch_isr_subscription_chf = fields.Char(string='CHF ISR Subscription Number', help='The subscription number provided by the bank or Postfinance to identify the bank, used to generate ISR in CHF. eg. 01-162-8')
    l10n_ch_isr_subscription_eur = fields.Char(string='EUR ISR Subscription Number', help='The subscription number provided by the bank or Postfinance to identify the bank, used to generate ISR in EUR. eg. 03-162-5')
    l10n_ch_show_subscription = fields.Boolean(compute='_compute_l10n_ch_show_subscription', default=lambda self: self.env.company.country_id.code == 'CH')

    def _is_isr_issuer(self):
        return (_is_l10n_ch_isr_issuer(self.l10n_ch_postal, 'CHF')
                or _is_l10n_ch_isr_issuer(self.l10n_ch_postal, 'EUR'))

    @api.constrains("l10n_ch_postal", "partner_id")
    def _check_postal_num(self):
        """Validate postal number format"""
        for rec in self:
            if rec.l10n_ch_postal and not _is_l10n_ch_postal(self.l10n_ch_postal):
                # l10n_ch_postal is used for the purpose of Client Number on your own accounts, so don't do the check there
                if rec.partner_id and not rec.partner_id.ref_company_ids:
                    raise ValidationError(
                        _("The postal number {} is not valid.\n"
                          "It must be a valid postal number format. eg. 10-8060-7").format(rec.l10n_ch_postal))
        return True

    @api.constrains("l10n_ch_isr_subscription_chf", "l10n_ch_isr_subscription_eur")
    def _check_subscription_num(self):
        """Validate ISR subscription number format
        Subscription number can only starts with 01 or 03
        """
        for rec in self:
            for currency in ["CHF", "EUR"]:
                subscrip = rec.l10n_ch_isr_subscription_chf if currency == "CHF" else rec.l10n_ch_isr_subscription_eur
                if subscrip and not _is_l10n_ch_isr_issuer(subscrip, currency):
                    example = "01-162-8" if currency == "CHF" else "03-162-5"
                    raise ValidationError(
                        _("The ISR subcription {} for {} number is not valid.\n"
                          "It must starts with {} and we a valid postal number format. eg. {}"
                          ).format(subscrip, currency, ISR_SUBSCRIPTION_CODE[currency], example))
        return True

    @api.depends('partner_id', 'company_id')
    def _compute_l10n_ch_show_subscription(self):
        for bank in self:
            if bank.partner_id:
                bank.l10n_ch_show_subscription = bool(bank.partner_id.ref_company_ids)
            elif bank.company_id:
                bank.l10n_ch_show_subscription = bank.company_id.country_id.code == 'CH'
            else:
                bank.l10n_ch_show_subscription = self.env.company.country_id.code == 'CH'

    @api.depends('acc_number', 'acc_type')
    def _compute_sanitized_acc_number(self):
        #Only remove spaces in case it is not postal
        postal_banks = self.filtered(lambda b: b.acc_type == "postal")
        for bank in postal_banks:
            bank.sanitized_acc_number = bank.acc_number
        super(ResPartnerBank, self - postal_banks)._compute_sanitized_acc_number()

    @api.model
    def _get_supported_account_types(self):
        rslt = super(ResPartnerBank, self)._get_supported_account_types()
        rslt.append(('postal', _('Postal')))
        return rslt

    @api.model
    def retrieve_acc_type(self, acc_number):
        """ Overridden method enabling the recognition of swiss postal bank
        account numbers.
        """
        acc_number_split = ""
        # acc_number_split is needed to continue to recognize the account
        # as a postal account even if the difference
        if acc_number and " " in acc_number:
            acc_number_split = acc_number.split(" ")[0]
        if _is_l10n_ch_postal(acc_number) or (acc_number_split and _is_l10n_ch_postal(acc_number_split)):
            return 'postal'
        else:
            return super(ResPartnerBank, self).retrieve_acc_type(acc_number)

    @api.onchange('acc_number', 'partner_id', 'acc_type')
    def _onchange_set_l10n_ch_postal(self):
        if self.acc_type == 'iban':
            self.l10n_ch_postal = self._retrieve_l10n_ch_postal(self.sanitized_acc_number)
        elif self.acc_type == 'postal':
            if self.acc_number and " " in self.acc_number:
                self.l10n_ch_postal = self.acc_number.split(" ")[0]
            else:
                self.l10n_ch_postal = self.acc_number
                # In case of ISR issuer, this number is not
                # unique and we fill acc_number with partner
                # name to give proper information to the user
                if self.partner_id and self.acc_number[:2] in ["01", "03"]:
                    self.acc_number = ("{} {}").format(self.acc_number, self.partner_id.name)

    @api.model
    def _is_postfinance_iban(self, iban):
        """Postfinance IBAN have format
        CHXX 0900 0XXX XXXX XXXX K
        Where 09000 is the clearing number
        """
        return iban.startswith('CH') and iban[4:9] == CLEARING

    @api.model
    def _pretty_postal_num(self, number):
        """format a postal account number or an ISR subscription number
        as per specifications with '-' separators.
        eg. 010001628 -> 01-162-8
        """
        if re.match('^[0-9]{2}-[0-9]{1,6}-[0-9]$', number or ''):
            return number
        currency_code = number[:2]
        middle_part = number[2:-1]
        trailing_cipher = number[-1]
        middle_part = middle_part.lstrip("0")
        return currency_code + '-' + middle_part + '-' + trailing_cipher

    @api.model
    def _retrieve_l10n_ch_postal(self, iban):
        """Reads a swiss postal account number from a an IBAN and returns it as
        a string. Returns None if no valid postal account number was found, or
        the given iban was not from Swiss Postfinance.

        CH09 0900 0000 1000 8060 7 -> 10-8060-7
        """
        if self._is_postfinance_iban(iban):
            # the IBAN corresponds to a swiss account
            return self._pretty_postal_num(iban[-9:])
        return None

    def find_number(self, s):
        # DEPRECATED FUNCTION: not used anymore. QR-bills don't use structured addresses
        # this regex match numbers like 1bis 1a
        lmo = re.findall('([0-9]+[^ ]*)',s)
        # no number found
        if len(lmo) == 0:
            return ''
        # Only one number or starts with a number return the first one
        if len(lmo) == 1 or re.match(r'^\s*([0-9]+[^ ]*)',s):
            return lmo[0]
        # else return the last one
        if len(lmo) > 1:
            return lmo[-1]
        else:
            return ''

    def _prepare_swiss_code_url_vals(self, amount, currency_name, debtor_partner, reference_type, reference, comment):
        creditor_addr_1, creditor_addr_2 = self._get_partner_address_lines(self.partner_id)
        debtor_addr_1, debtor_addr_2 = self._get_partner_address_lines(debtor_partner)

        return [
            'SPC',                                                # QR Type
            '0200',                                               # Version
            '1',                                                  # Coding Type
            self.sanitized_acc_number,                            # IBAN
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
            currency_name,                                        # Currency
            'K',                                                  # Ultimate Debtor Address Type
            debtor_partner.name[:70],                             # Ultimate Debtor Name
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

    @api.model
    def build_swiss_code_url(self, amount, currency_name, not_used_anymore_1, debtor_partner, not_used_anymore_2, structured_communication, free_communication):
        comment = ""
        if free_communication:
            comment = (free_communication[:137] + '...') if len(free_communication) > 140 else free_communication

        # Compute reference type (empty by default, only mandatory for QR-IBAN,
        # and must then be 27 characters-long, with mod10r check digit as the 27th one,
        # just like ISR number for invoices)
        reference_type = 'NON'
        reference = ''
        if self._is_qr_iban():
            # _check_for_qr_code_errors ensures we can't have a QR-IBAN without a QR-reference here
            reference_type = 'QRR'
            reference = structured_communication

        qr_code_vals = self._prepare_swiss_code_url_vals(amount, currency_name, debtor_partner, reference_type, reference, comment)

        # use quiet to remove blank around the QR and make it easier to place it
        return '/report/barcode/?type=%s&value=%s&width=%s&height=%s&quiet=1' % ('QR', werkzeug.urls.url_quote_plus('\n'.join(qr_code_vals)), 256, 256)

    def _get_partner_address_lines(self, partner):
        """ Returns a tuple of two elements containing the address lines to use
        for this partner. Line 1 contains the street and number, line 2 contains
        zip and city. Those two lines are limited to 70 characters
        """
        streets = [partner.street, partner.street2]
        line_1 = ' '.join(filter(None, streets))
        line_2 = partner.zip + ' ' + partner.city
        return line_1[:70], line_2[:70]

    def _check_qr_iban_range(self, iban):
        if not iban or len(iban) < 9:
            return False
        iid_start_index = 4
        iid_end_index = 8
        iid = iban[iid_start_index : iid_end_index+1]
        return re.match('\d+', iid) \
               and 30000 <= int(iid) <= 31999 # Those values for iid are reserved for QR-IBANs only

    def _is_qr_iban(self):
        """ Tells whether or not this bank account has a QR-IBAN account number.
        QR-IBANs are specific identifiers used in Switzerland as references in
        QR-codes. They are formed like regular IBANs, but are actually something
        different.
        """
        self.ensure_one()
        return self.acc_type == 'iban' \
               and self._check_qr_iban_range(self.sanitized_acc_number)

    @api.model
    def _is_qr_reference(self, reference):
        """ Checks whether the given reference is a QR-reference, i.e. it is
        made of 27 digits, the 27th being a mod10r check on the 26 previous ones.
        """
        return reference \
               and len(reference) == 27 \
               and re.match('\d+$', reference) \
               and reference == mod10r(reference[:-1])

    def validate_swiss_code_arguments(self, currency, debtor_partner, reference_to_check=''):
        # reference_to_check added as an optional parameter in order not to break our stability policy.
        # For people having already installed the module, QRR won't be checked until
        # they update the module (as a change in the pdf report's xml sets a value in reference_to_check).
        # '' is used as default, as an empty field will pass None value,
        # and we want to be able to distinguish between those cases
        def _partner_fields_set(partner):
            return partner.zip and \
                   partner.city and \
                   partner.country_id.code and \
                   (partner.street or partner.street2)

        return _partner_fields_set(self.partner_id) and \
               _partner_fields_set(debtor_partner) and \
               (reference_to_check == '' or not self._is_qr_iban() or self._is_qr_reference(reference_to_check))
