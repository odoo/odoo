# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import re


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
            "CHECK(l10n_it_codice_fiscale IS NULL OR l10n_it_codice_fiscale = '' OR LENGTH(l10n_it_codice_fiscale) >= 11)",
            "Codice fiscale must have between 11 and 16 characters."),

        ('l10n_it_pa_index',
            "CHECK(l10n_it_pa_index IS NULL OR l10n_it_pa_index = '' OR LENGTH(l10n_it_pa_index) >= 6)",
            "PA index must have between 6 and 7 characters."),
    ]

    @api.model
    def _l10n_it_normalize_codice_fiscale(self, codice):
        if re.match(r'^IT[0-9]{11}$', codice):
            return codice[2:13]
        return codice

    @api.onchange('vat', 'country_id')
    def _l10n_it_onchange_vat(self):
        if not self.l10n_it_codice_fiscale and self.vat and (self.country_id.code == "IT" or self.vat.startswith("IT")):
            self.l10n_it_codice_fiscale = self._l10n_it_normalize_codice_fiscale(self.vat)
        elif self.country_id.code not in [False, "IT"]:
            self.l10n_it_codice_fiscale = ""

    @api.constrains('l10n_it_codice_fiscale')
    def validate_codice_fiscale(self):
        p = re.compile(r'^([A-Za-z]{6}[0-9]{2}[A-Za-z]{1}[0-9]{2}[A-Za-z]{1}[0-9]{3}[A-Za-z]{1}$)|([0-9]{11})|(IT[0-9]{11})$')
        for record in self:
            if record.l10n_it_codice_fiscale and not p.match(record.l10n_it_codice_fiscale):
                raise UserError(_("Invalid Codice Fiscale '%s': should be like 'MRTMTT91D08F205J' for physical person and '12345678901' or 'IT12345678901' for businesses.", record.l10n_it_codice_fiscale))
