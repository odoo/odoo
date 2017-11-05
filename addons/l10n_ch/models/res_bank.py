# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.tools.misc import mod10r


def _is_l10n_ch_postal(account_ref):
    """ Returns True iff the string account_ref is a valid postal account number,
    i.e. it only contains ciphers and is last cipher is the result of a recursive
    modulo 10 operation ran over the rest of it.
    """
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

    l10n_ch_postal = fields.Char(help='The ISR number of the company within the bank', compute='_compute_l10n_ch_postal')

    @api.depends('acc_number')
    def _compute_acc_type(self):
        """ Overridden method enabling the recognition of swiss postal bank
        account numbers.
        """
        for record in self:
            if _is_l10n_ch_postal(record.acc_number):
                record.acc_type = 'postal'
            else:
                super(ResPartnerBank, record)._compute_acc_type()

    @api.depends('acc_number')
    def _compute_l10n_ch_postal(self):
        for record in self:
            if record.acc_type == 'postal':
                record.l10n_ch_postal = record.sanitized_acc_number
            elif record.acc_type == 'iban':
                record.l10n_ch_postal = record._retrieve_l10n_ch_postal(record.sanitized_acc_number)

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
