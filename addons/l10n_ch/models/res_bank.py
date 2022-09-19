# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from stdnum.util import clean

from odoo import api, fields, models, _
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.base_iban.models.res_partner_bank import normalize_iban, pretty_iban, validate_iban
from odoo.exceptions import ValidationError
from odoo.tools.misc import mod10r


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

def validate_qr_iban(qr_iban):
    # Check first if it's a valid IBAN.
    validate_iban(qr_iban)

    # We sanitize first so that _check_qr_iban_range() can extract correct IID from IBAN to validate it.
    sanitized_qr_iban = sanitize_account_number(qr_iban)

    if sanitized_qr_iban[:2] not in ['CH', 'LI']:
        raise ValidationError(_("QR-IBAN numbers are only available in Switzerland."))

    # Now, check if it's valid QR-IBAN (based on its IID).
    if not check_qr_iban_range(sanitized_qr_iban):
        raise ValidationError(_("QR-IBAN '%s' is invalid.") % qr_iban)

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

    l10n_ch_postal = fields.Char(
        string="Swiss Postal Account",
        readonly=False, store=True,
        compute='_compute_l10n_ch_postal',
        help="This field is used for the Swiss postal account number on a vendor account and for the client number on "
             "your own account. The client number is mostly 6 numbers without -, while the postal account number can "
             "be e.g. 01-162-8")

    l10n_ch_qr_iban = fields.Char(string='QR-IBAN',
                                  compute='_compute_l10n_ch_qr_iban',
                                  store=True,
                                  readonly=False,
                                  help="Put the QR-IBAN here for your own bank accounts.  That way, you can "
                                       "still use the main IBAN in the Account Number while you will see the "
                                       "QR-IBAN for the barcode.  ")

    # fields to configure ISR payment slip generation
    l10n_ch_isr_subscription_chf = fields.Char(string='CHF ISR Subscription Number', help='The subscription number provided by the bank or Postfinance to identify the bank, used to generate ISR in CHF. eg. 01-162-8')
    l10n_ch_isr_subscription_eur = fields.Char(string='EUR ISR Subscription Number', help='The subscription number provided by the bank or Postfinance to identify the bank, used to generate ISR in EUR. eg. 03-162-5')
    l10n_ch_show_subscription = fields.Boolean(compute='_compute_l10n_ch_show_subscription', default=lambda self: self.env.company.account_fiscal_country_id.code == 'CH')

    def _is_isr_issuer(self):
        return (_is_l10n_ch_isr_issuer(self.l10n_ch_postal, 'CHF')
                or _is_l10n_ch_isr_issuer(self.l10n_ch_postal, 'EUR'))

    @api.constrains("l10n_ch_postal", "partner_id")
    def _check_postal_num(self):
        """Validate postal number format"""
        for rec in self:
            if rec.l10n_ch_postal and not _is_l10n_ch_postal(rec.l10n_ch_postal):
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
                bank.l10n_ch_show_subscription = bank.partner_id.ref_company_ids.country_id.code in ('CH', 'LI')
            elif bank.company_id:
                bank.l10n_ch_show_subscription = bank.company_id.account_fiscal_country_id.code in ('CH', 'LI')
            else:
                bank.l10n_ch_show_subscription = self.env.company.account_fiscal_country_id.code in ('CH', 'LI')

    @api.depends('acc_number', 'acc_type')
    def _compute_sanitized_acc_number(self):
        #Only remove spaces in case it is not postal
        postal_banks = self.filtered(lambda b: b.acc_type == "postal")
        for bank in postal_banks:
            bank.sanitized_acc_number = bank.acc_number
        super(ResPartnerBank, self - postal_banks)._compute_sanitized_acc_number()

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

    @api.model
    def create(self, vals):
        if vals.get('l10n_ch_qr_iban'):
            validate_qr_iban(vals['l10n_ch_qr_iban'])
            vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().create(vals)

    def write(self, vals):
        if vals.get('l10n_ch_qr_iban'):
            validate_qr_iban(vals['l10n_ch_qr_iban'])
            vals['l10n_ch_qr_iban'] = pretty_iban(normalize_iban(vals['l10n_ch_qr_iban']))
        return super().write(vals)

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

    @api.depends('acc_number', 'partner_id', 'acc_type')
    def _compute_l10n_ch_postal(self):
        for record in self:
            if record.acc_type == 'iban':
                record.l10n_ch_postal = self._retrieve_l10n_ch_postal(record.sanitized_acc_number)
            elif record.acc_type == 'postal':
                if record.acc_number and " " in record.acc_number:
                    record.l10n_ch_postal = record.acc_number.split(" ")[0]
                else:
                    record.l10n_ch_postal = record.acc_number
                    # In case of ISR issuer, this number is not
                    # unique and we fill acc_number with partner
                    # name to give proper information to the user
                    if record.partner_id and record.acc_number[:2] in ["01", "03"]:
                        record.acc_number = ("{} {}").format(record.acc_number, record.partner_id.name)

    @api.model
    def _is_postfinance_iban(self, iban):
        """Postfinance IBAN have format
        CHXX 0900 0XXX XXXX XXXX K
        Where 09000 is the clearing number
        """
        return iban.startswith(('CH', 'LI')) and iban[4:9] == CLEARING

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

    def _l10n_ch_get_qr_vals(self, amount, currency, debtor_partner, free_communication, structured_communication):
        comment = ""
        if free_communication:
            comment = (free_communication[:137] + '...') if len(free_communication) > 140 else free_communication

        creditor_addr_1, creditor_addr_2 = self._get_partner_address_lines(self.partner_id)
        debtor_addr_1, debtor_addr_2 = self._get_partner_address_lines(debtor_partner)

        # Compute reference type (empty by default, only mandatory for QR-IBAN,
        # and must then be 27 characters-long, with mod10r check digit as the 27th one,
        # just like ISR number for invoices)
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
               and re.match('\d+$', reference) \
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

    def _eligible_for_qr_code(self, qr_method, debtor_partner, currency):
        if qr_method == 'ch_qr':

            return self.acc_type == 'iban' and \
                   self.partner_id.country_id.code == 'CH' and \
                   (not debtor_partner or debtor_partner.country_id.code in ('CH', 'LI')) \
                   and currency.name in ('EUR', 'CHF')

        return super()._eligible_for_qr_code(qr_method, debtor_partner, currency)

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

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('ch_qr', _("Swiss QR bill"), 10))
        return rslt
