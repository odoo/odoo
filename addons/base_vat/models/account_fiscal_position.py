# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.constrains('country_id', 'foreign_vat')
    def _validate_foreign_vat(self):
        for record in self:
            if not record.foreign_vat:
                continue

            if record.country_group_id:
                # Checks the foreign vat is a VAT Number linked to a country of the country group
                foreign_vat_country_id = next((country_id for country_id in self.country_group_id.country_ids if country_id.code.upper() == self.foreign_vat[:2]), False)
                if not foreign_vat_country_id:
                    raise ValidationError(_("The country detected for this foreign VAT number does not match any of the countries composing the country group set on this fiscal position."))
                if record.country_id:
                    checked_country_code = self.env['res.partner']._run_vat_test(record.foreign_vat, record.country_id) or self.env['res.partner']._run_vat_test(record.foreign_vat, foreign_vat_country_id)
                    if not checked_country_code:
                        record.raise_vat_error_message(foreign_vat_country_id)
                else:
                    # If no country is assigned then assign the country of the foreign vat for the mapping
                    record.country_id = foreign_vat_country_id
                    checked_country_code = self.env['res.partner']._run_vat_test(record.foreign_vat, foreign_vat_country_id)
                    if not checked_country_code:
                        record.raise_vat_error_message(record.country_id)
            elif record.country_id:
                foreign_vat_country_id = self.env['res.country'].search([('code', '=', record.foreign_vat[:2].upper())], limit=1)
                checked_country_code = self.env['res.partner']._run_vat_test(record.foreign_vat, foreign_vat_country_id or record.country_id)
                if not checked_country_code:
                    record.raise_vat_error_message()

    def raise_vat_error_message(self, country=False):
        fp_label = _("fiscal position [%s]", self.name)
        country_code = country.code.lower() if country else self.country_id.code.lower()
        error_message = self.env['res.partner']._build_vat_error_message(country_code, self.foreign_vat, fp_label)
        raise ValidationError(error_message)
