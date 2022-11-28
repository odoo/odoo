# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

def mod11ini(value):
    '''
    Compute mod11ini
    copied from account_reference / KGB
    '''
    length = len(value)
    s = 0
    for i in range(0, length):
        s += int(value[length - i - 1]) * (i + 2)
    res = s % 11
    if res > 1:
        res = 11 - res
    else:
        res = 0
    return str(res)

class AccountMove(models.Model):
    _inherit = 'account.move'

    """
    account.move object: add support for Croatian structured communication
    Only partial implementation of HR regulative (most commonly used):
    https://www.fina.hr/documents/52450/238316/Jedinstveni+pregled+osnovnih+modela+poziva+na+broj+-+primjena+travanj+2022.pdf
    Covered references 
    HR00        P1 - P2 - P3        - No control
    HR01        (P1 - P2 - P3)K     - Checksum contorll (mod10-11)
    """

    def _get_l10n_hr_reference_elements(self):
        """
        Inheritable for fine tuned data
        :return: P1 P2 P3 numerical elements
        """
        self.ensure_one()
        p1 = str(self.date.year) + str(self.date.month)
        p2 = str(self.id)
        p3 = str(self.partner_id.id)
        return p1, p2, p3

    def _l10n_hr_reference_number_get(self, model=None, p1='', p2='', p3=''):
        if model == "HR01":
            res = '-'.join((p1, p2, p3 + mod11ini(p1 + p2 + p3)))
        elif model == "HR00":
            res = '-'.join([p1, p2, p3])
        res = '-'.join((model, res))
        return res

    def _get_invoice_reference_hr_partner(self):
        """ This computes the reference based on the Croatian national standard HR00
            numnerical paramaters p1, p2, p3 are optional and without any controll
        """
        self.ensure_one()
        p1, p2, p3 = self._get_l10n_hr_reference_elements()
        return self._l10n_hr_reference_number_get('HR00', p1, p2, p3)

    def _get_invoice_reference_hr_invoice(self):
        """ This computes the reference based on the croatian national standard HR01
            numnerical paramaters p1, p2, p3 are optional but if entered, checksum is calculated
        """
        self.ensure_one()
        p1, p2, p3 = self._get_l10n_hr_reference_elements()
        return self._l10n_hr_reference_number_get('HR01', p1, p2, p3)
