# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_br_cpf_code = fields.Char(string="CPF", help="Natural Persons Register.")
    l10n_br_ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.")
    l10n_br_im_code = fields.Char(string="IM", help="Municipal Tax Identification Number")
    l10n_br_isuf_code = fields.Char(string="SUFRAMA code", help="SUFRAMA registration number.")

    @api.constrains("vat")
    def check_vat(self):
        '''
        Example of a Brazilian CNPJ number: 76.634.583/0001-74.
        The 13th digit is the check digit of the previous 12 digits.
        The check digit is calculated by multiplying the first 12 digits by weights and calculate modulo 11 of the result.
        The 14th digit is the check digit of the previous 13 digits. Calculated the same way.
        Both remainders are appended to the first 12 digits.
        '''
        def _l10n_br_calculate_mod_11(check, weights):
            result = (sum([i*j for (i, j) in zip(check, weights)])) % 11
            if result <= 1:
                return 0
            return 11 - result
        def _l10n_br_is_valid_cnpj(vat_clean):
            weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            vat_check = vat_clean[:12]
            vat_check.append(_l10n_br_calculate_mod_11(vat_check, weights[1:]))
            vat_check.append(_l10n_br_calculate_mod_11(vat_check, weights))
            return vat_check == vat_clean

        def _l10n_br_is_valid_cpf(vat_clean): #http://www.receita.fazenda.gov.br/aplicacoes/atcta/cpf/funcoes.js
            total_sum = 0
            # If the CPF list contains all zeros, it's not valid
            if vat_clean == [0] * 11:
                return False
            # Calculate the sum for the first verification digit
            for i in range(1, 10):
                total_sum = total_sum + vat_clean[i - 1] * (11 - i)
            remainder = (total_sum * 10) % 11
            # If the remainder is 10 or 11, set it to 0
            if remainder in (10, 11):
                remainder = 0
            # Check the first verification digit
            if remainder != vat_clean[9]:
                return False
            total_sum = 0
            # Calculate the sum for the second verification digit
            for i in range(1, 11):
                total_sum = total_sum + vat_clean[i - 1] * (12 - i)
            remainder = (total_sum * 10) % 11
            # If the remainder is 10 or 11, set it to 0
            if remainder in (10, 11):
                remainder = 0
            # Check the second verification digit
            if remainder != vat_clean[10]:
                return False
            return True

        for partner in self:
            if not partner.vat:
                return
            if not partner.country_code == 'BR':
                return super().check_vat()
            vat_clean = list(map(int, re.sub("[^0-9]", "", partner.vat)))
            if len(vat_clean) == 14:
                if not _l10n_br_is_valid_cnpj(vat_clean):
                    raise ValidationError(_("Invalid CNPJ. Make sure that all the digits are entered correctly."))
            elif len(vat_clean) == 11:
                if not _l10n_br_is_valid_cpf(vat_clean):
                    raise ValidationError(_("Invalid CPF. Make sure that all the digits are entered correctly."))
            else:
                raise ValidationError(_("Invalid CNPJ/CPF. Make sure that the CNPJ is a 14 digits number or CPF is a 11 digits number."))
