# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_it_pec_email = fields.Char(string="PEC e-mail")
    l10n_it_codice_fiscale = fields.Char(string="Codice Fiscale", size=16)
    l10n_it_pa_index = fields.Char(string="PA index",
        size=7,
        help="Must contain the 6-character (or 7) code, present in the PA\
              Index in the information relative to the electronic invoicing service,\
              associated with the office which, within the addressee administration, deals\
              with receiving (and processing) the invoice.")

    _sql_constraints = [
        ('l10n_it_codice_fiscale',
            "CHECK(l10n_it_codice_fiscale IS NULL OR LENGTH(l10n_it_codice_fiscale) >= 11)",
            "Codice fiscale must have between 11 and 16 characters."),

        ('l10n_it_pa_index',
            "CHECK(l10n_it_pa_index IS NULL OR LENGTH(l10n_it_pa_index) >= 6)",
            "PA index must have between 6 and 7 characters."),
    ]
