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

            checked_country_code = self.env['res.partner']._run_vat_test(record.foreign_vat, record.country_id)

            if checked_country_code and checked_country_code != record.country_id.code.lower():
                raise ValidationError(_("The country detected for this foreign VAT number does not match the one set on this fiscal position."))

            if not checked_country_code:
                fp_label = _("fiscal position [%s]", record.name)
                error_message = self.env['res.partner']._build_vat_error_message(record.country_id.code.lower(), record.foreign_vat, fp_label)
                raise ValidationError(error_message)

    def _get_vat_valid(self, delivery, company=None):
        eu_countries = self.env.ref('base.europe').country_ids

        # If VIES validation does not apply to this partner (e.g. they
        # are in the same country as the partner), then skip.
        if not (company and delivery.with_company(company).perform_vies_validation):
            return super()._get_vat_valid(delivery, company)

        # If the company has a fiscal position with a foreign vat in Europe, in the same country as the partner, then the VIES validity applies
        if self.search_count([
                *self._check_company_domain(company),
                ('foreign_vat', '!=', False),
                ('country_id', '=', delivery.country_id.id),
        ]) or company.country_id in eu_countries:
            return super()._get_vat_valid(delivery, company) and delivery.vies_valid

        return super()._get_vat_valid(delivery, company)
