# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    pec_email = fields.Char(string="PEC e-mail")
    codice_fiscale = fields.Char(string="Codice Fiscale", size=16)
    pa_index = fields.Char(string="PA index",
                           size=7,
                           help="Must contain the 6-character (or 7) code, present in the PA\
                                   Index in the information relative to the electronic invoicing service,\
                                   associated with the office which, within the addressee administration, deals\
                                   with receiving (and processing) the invoice.")

    @api.constrains('codice_fiscale')
    def _check_codice_fiscale(self):
        for record in self:
            if not record.codice_fiscale:
                continue
            if len(record.codice_fiscale) < 11:
                raise ValidationError("Codice fiscale must have between 11 and 16 characters.")

    @api.constrains('pa_index')
    def _check_pa_index(self):
        for record in self:
            if not record.pa_index:
                continue
            if len(record.pa_index) < 6:
                raise ValidationError("PA index must have between 6 and 7 characters.")
