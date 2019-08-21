# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.tools.misc import mod10r
from odoo.exceptions import ValidationError

import werkzeug.urls

CH_POSTFINANCE_CLEARING = "09000"


def validate_l10n_ch_postal(postal_acc_number):
    """Check if the string postal_acc_number is a valid postal account number,
    i.e. it only contains ciphers and is last cipher is the result of a recursive
    modulo 10 operation ran over the rest of it. Shorten form with - is also accepted.
    Raise a ValidationError if check fails
    """
    if not postal_acc_number:
        raise ValidationError(_("There is no postal account number."))
    if re.match('^[0-9]{2}-[0-9]{1,6}-[0-9]$', postal_acc_number or ''):
        ref_subparts = postal_acc_number.split('-')
        postal_acc_number = ref_subparts[0] + ref_subparts[1].rjust(6,'0') + ref_subparts[2]

    if not re.match('\d{9}$', postal_acc_number or ''):
        raise ValidationError(_("The postal does not match 9 digits position."))

    acc_number_without_check = postal_acc_number[:-1]
    if not mod10r(acc_number_without_check) == postal_acc_number:
        raise ValidationError(_("The postal account number is not valid."))

def pretty_l10n_ch_postal(number):
    """format a postal account number or an ISR subscription number
    as per specifications with '-' separators.
    eg. 010000628 -> 01-162-8
    """
    if re.match('^[0-9]{2}-[0-9]{1,6}-[0-9]$', number or ''):
        return number
    currency_code = number[:2]
    middle_part = number[2:-1]
    trailing_cipher = number[-1]
    middle_part = re.sub('^0*', '', middle_part)
    return currency_code + '-' + middle_part + '-' + trailing_cipher

def _is_l10n_ch_postfinance_iban(iban):
    """Postfinance IBAN have format
    CHXX 0900 0XXX XXXX XXXX K
    Where 09000 is the clearing number
    """
    return (iban.startswith('CH')
            and iban[4:9] == CH_POSTFINANCE_CLEARING)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ch_postal = fields.Char(string='Swiss postal account', help='Swiss postal account number eg. 01-162-8')
    # fields to configure ISR payment slip generation
    l10n_ch_isr_subscription_chf = fields.Char(string='CHF ISR subscription number', help='The subscription number provided by the bank or Postfinance, used to generate ISR in CHF. eg. 01-162-8')
    l10n_ch_isr_subscription_eur = fields.Char(string='EUR ISR subscription number', help='The subscription number provided by the bank or Postfinance, used to generate ISR in EUR. eg. 03-162-5')

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
        try:
            validate_l10n_ch_postal(acc_number)
            return 'postal'
        except ValidationError:
            return super(ResPartnerBank, self).retrieve_acc_type(acc_number)

    @api.onchange('acc_number')
    def _onchange_set_l10n_ch_postal(self):
        if self.acc_type == 'iban':
            self.l10n_ch_postal = self._retrieve_l10n_ch_postal(self.sanitized_acc_number)
        elif self.acc_type == 'postal':
            self.l10n_ch_postal = self.acc_number

    @api.model
    def _retrieve_l10n_ch_postal(self, iban):
        """Reads a swiss postal account number from a an IBAN and returns it as
        a string. Returns None if no valid postal account number was found, or
        the given iban was not from Swiss Postfinance.

        CH09 0900 0000 1000 8060 7 -> 10-8060-7
        """
        # We can deduce postal account number only if
        # the financial institution is PostFinance
        if _is_l10n_ch_postfinance_iban(iban):
            #the IBAN corresponds to a swiss account
            try:
                validate_l10n_ch_postal(iban[-9:])
                return pretty_l10n_ch_postal(iban[-9:])
            except ValidationError:
                pass
        return None

    @api.model
    def create(self, vals):
        if vals.get('l10n_ch_postal'):
            try:
                validate_l10n_ch_postal(vals['l10n_ch_postal'])
                vals['l10n_ch_postal'] = pretty_l10n_ch_postal(vals['l10n_ch_postal'])
            except ValidationError:
                pass
        return super(ResPartnerBank, self).create(vals)

    def write(self, vals):
        if vals.get('l10n_ch_postal'):
            try:
                validate_l10n_ch_postal(vals['l10n_ch_postal'])
                vals['l10n_ch_postal'] = pretty_l10n_ch_postal(vals['l10n_ch_postal'])
            except ValidationError:
                pass
        return super(ResPartnerBank, self).write(vals)

    def find_number(self, s):
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

    @api.model
    def build_swiss_code_url(self, amount, currency, date_due, debitor, ref_type, reference, comment):
        communication = ""
        if comment:
            communication = (comment[:137] + '...') if len(comment) > 140 else comment

        t_street_comp = '%s %s' % (self.company_id.street if (self.company_id.street != False) else '', self.company_id.street2 if (self.company_id.street2 != False) else '')
        t_street_deb = '%s %s' % (debitor.street if (debitor.street != False) else '', debitor.street2 if (debitor.street2 != False) else '')
        number = self.find_number(t_street_comp)
        number_deb = self.find_number(t_street_deb)
        if (t_street_comp == ' '):
            t_street_comp = False
        if (t_street_deb == ' '):
            t_street_deb = False

        qr_code_string = 'SPC\n0100\n1\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s' % (
                          self.acc_number,
                          self.company_id.name,
                          t_street_comp,
                          number,
                          self.company_id.zip,
                          self.company_id.city,
                          self.company_id.country_id.code,
                          amount,
                          currency,
                          date_due,
                          debitor.name,
                          t_street_deb,
                          number_deb,
                          debitor.zip,
                          debitor.city,
                          debitor.country_id.code,
                          ref_type,
                          reference,
                          communication)
        qr_code_url = '/report/barcode/?type=%s&value=%s&width=%s&height=%s&humanreadable=1' % ('QR', werkzeug.url_quote_plus(qr_code_string), 256, 256)
        return qr_code_url

    @api.model
    def validate_swiss_code_arguments(self, currency, debitor):

        t_street_comp = '%s %s' % (self.company_id.street if (self.company_id.street != False) else '', self.company_id.street2 if (self.company_id.street2 != False) else '')
        t_street_deb = '%s %s' % (debitor.street if (debitor.street != False) else '', debitor.street2 if (debitor.street2 != False) else '')
        number = self.find_number(t_street_comp)
        number_deb = self.find_number(t_street_deb)
        if (t_street_comp == ' '):
            t_street_comp = False
        if (t_street_deb == ' '):
            t_street_deb = False

        if(currency.name == 'EUR'):
            return (self.l10n_ch_postal_subscription_eur and
                    self.company_id.zip and
                    self.company_id.city and
                    self.company_id.country_id.code and
                    (t_street_comp != False) and
                    (t_street_deb != False) and
                    debitor.zip and
                    debitor.city and
                    debitor.country_id.code and
                    (number != False) and (number_deb != False))
        elif(currency.name == 'CHF'):
            return (self.l10n_ch_postal_subscription_chf and
                    self.company_id.zip and
                    self.company_id.city and
                    self.company_id.country_id.code and
                    (t_street_comp != False) and
                    (t_street_deb != False) and
                    debitor.zip and
                    debitor.city and
                    debitor.country_id.code and
                    (number != False) and (number_deb != False))
        else:
            return False
