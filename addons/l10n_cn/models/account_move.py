# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    fapiao = fields.Char(string='Fapiao Number', size=8, copy=False, tracking=True)

    @api.constrains('fapiao')
    def _check_fapiao(self):
        for record in self:
            if record.fapiao and (len(record.fapiao) != 8 or not record.fapiao.isdecimal()):
                raise ValidationError(_("Fapiao number is an 8-digit number. Please enter a correct one."))
