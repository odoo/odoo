# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    aba_bsb = fields.Char(string='BSB', help='Bank State Branch code - needed if payment is to be made using ABA files')

    @api.model
    def _get_supported_account_types(self):
        rslt = super(ResPartnerBank, self)._get_supported_account_types()
        rslt.append(('aba', _('ABA')))
        return rslt

    @api.constrains('aba_bsb')
    def _validate_aba_bsb(self):
        for record in self:
            if record.aba_bsb:
                test_bsb = re.sub('( |-)', '', record.aba_bsb)
                if len(test_bsb) != 6 or not test_bsb.isdigit():
                    raise ValidationError(_('BSB is not valid (expected format is "NNN-NNN"). Please rectify.'))

    @api.depends('acc_number')
    def _compute_acc_type(self):
        """ Criteria to be an ABA account:
            - Spaces, hypens, digits are valid.
            - Total length must be 9 or less.
            - Cannot be only spaces, zeros or hyphens (must have at least one digit in range 1-9)
        """
        super()._compute_acc_type()
        for rec in self:
            if rec.acc_type == 'bank' and re.match(r"^(?=.*[1-9])[ \-\d]{0,9}$", rec.acc_number or ''):
                rec.acc_type = 'aba'
