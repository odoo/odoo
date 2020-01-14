# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.tools.misc import mod10r

import werkzeug.urls

def _is_l10n_ch_postal(account_ref):
    """ Returns True iff the string account_ref is a valid postal account number,
    i.e. it only contains ciphers and is last cipher is the result of a recursive
    modulo 10 operation ran over the rest of it. Shorten form with - is also accepted.
    """
    if re.match('^[0-9]{2}-[0-9]{1,6}-[0-9]$', account_ref or ''):
        ref_subparts = account_ref.split('-')
        account_ref = ref_subparts[0] + ref_subparts[1].rjust(6,'0') + ref_subparts[2]

    if re.match('\d+$', account_ref or ''):
        account_ref_without_check = account_ref[:-1]
        return mod10r(account_ref_without_check) == account_ref
    return False


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_ch_postal_chf = fields.Char(string='CHF ISR reference', help='The postal reference of the bank, used to generate ISR payment slips in CHF.')
    l10n_ch_postal_eur = fields.Char(string='EUR ISR reference', help='The postal reference of the bank, used to generate ISR payment slips in EUR.')


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ch_postal = fields.Char(string='ISR reference', help='The ISR number of the company within the bank')

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
        if _is_l10n_ch_postal(acc_number):
            return 'postal'
        else:
            return super(ResPartnerBank, self).retrieve_acc_type(acc_number)

    @api.onchange('acc_number')
    def _onchange_set_l10n_ch_postal(self):
        if self.acc_type == 'iban':
            self.l10n_ch_postal = self._retrieve_l10n_ch_postal(self.sanitized_acc_number)
        else:
            self.l10n_ch_postal = self.sanitized_acc_number

    @api.model
    def _retrieve_l10n_ch_postal(self, iban):
        """ Reads a swiss postal account number from a an IBAN and returns it as
        a string. Returns None if no valid postal account number was found, or
        the given iban was not from Switzerland.
        """
        if iban[:2] == 'CH':
            #the IBAN corresponds to a swiss account
            if _is_l10n_ch_postal(iban[-12:]):
                return iban[-12:]
        return None

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

    def validate_swiss_code_arguments(self, currency, debitor):
        currency = currency or self.company_id.currency_id
        t_street_comp = '%s %s' % (self.company_id.street if (self.company_id.street != False) else '', self.company_id.street2 if (self.company_id.street2 != False) else '')
        t_street_deb = '%s %s' % (debitor.street if (debitor.street != False) else '', debitor.street2 if (debitor.street2 != False) else '')
        number = self.find_number(t_street_comp)
        number_deb = self.find_number(t_street_deb)
        if (t_street_comp == ' '):
            t_street_comp = False
        if (t_street_deb == ' '):
            t_street_deb = False

        if(currency.name == 'EUR'):
            return (self.bank_id.l10n_ch_postal_eur and
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
            return (self.bank_id.l10n_ch_postal_chf and
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
