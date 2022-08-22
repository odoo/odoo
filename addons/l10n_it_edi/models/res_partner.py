# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.it import codicefiscale, iva

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import re


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_it_pec_email = fields.Char(string="PEC e-mail")
    l10n_it_pa_index = fields.Char(string="PA index",
        size=7,
        help="Must contain the 6-character (or 7) code, present in the PA\
              Index in the information relative to the electronic invoicing service,\
              associated with the office which, within the addressee administration, deals\
              with receiving (and processing) the invoice.")

    _sql_constraints = [
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
        if not self.company_registry and self.vat and (self.country_id.code == "IT" or self.vat.startswith("IT")):
            self.company_registry = self._l10n_it_normalize_codice_fiscale(self.vat)
        elif self.country_id.code not in [False, "IT"]:
            self.company_registry = ""

    @api.constrains('company_registry')
    def validate_codice_fiscale(self):
        for record in self:
            if record.country_code == 'IT' and record.company_registry and (not codicefiscale.is_valid(record.company_registry) and not iva.is_valid(record.company_registry)):
                raise UserError(_("Invalid Codice Fiscale '%s': should be like 'MRTMTT91D08F205J' for physical person and '12345670546' or 'IT12345670546' for businesses.", record.company_registry))
