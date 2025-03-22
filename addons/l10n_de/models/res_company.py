# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import stdnum.de.stnr
import stdnum.exceptions


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_de_stnr = fields.Char(
        string="St.-Nr.",
        help="Tax number. Scheme: ??FF0BBBUUUUP, e.g.: 2893081508152 https://de.wikipedia.org/wiki/Steuernummer",
        tracking=True,
    )
    l10n_de_widnr = fields.Char(string="W-IdNr.", help="Business identification number.", tracking=True)

    def write(self, vals):
        if (
            'account_fiscal_country_id' in vals
            and (german_companies := self.filtered(lambda c: c.account_fiscal_country_id.code == 'DE'))
            and self.env['account.move'].search_count([('company_id', 'in', german_companies.ids)], limit=1)
        ):
            raise ValidationError(_("You cannot change the fiscal country."))
        return super().write(vals)

    @api.depends('country_code')
    @api.constrains('state_id', 'l10n_de_stnr')
    def _validate_l10n_de_stnr(self):
        for record in self:
            record.get_l10n_de_stnr_national()

    def get_l10n_de_stnr_national(self):
        self.ensure_one()
        national_steuer_nummer = None

        if self.l10n_de_stnr and self.country_code == 'DE':
            try:
                national_steuer_nummer = stdnum.de.stnr.to_country_number(self.l10n_de_stnr, self.state_id.name)
            except stdnum.exceptions.InvalidComponent:
                raise ValidationError(_("Your company's SteuerNummer is not compatible with your state"))
            except stdnum.exceptions.InvalidFormat:
                if stdnum.de.stnr.is_valid(self.l10n_de_stnr, self.state_id.name):
                    national_steuer_nummer = self.l10n_de_stnr
                else:
                    raise ValidationError(_("Your company's SteuerNummer is not valid"))

        elif self.l10n_de_stnr:
            national_steuer_nummer = self.l10n_de_stnr

        return national_steuer_nummer
