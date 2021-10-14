# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountTaxUnit(models.Model):
    _inherit = 'account.tax.unit'

    @api.constrains('country_id', 'vat')
    def _validate_vat(self):
        for record in self:
            if not record.vat:
                continue

            checked_country_code = self.env['res.partner']._run_vat_test(record.vat, record.country_id)

            if checked_country_code and checked_country_code != record.country_id.code.lower():
                raise ValidationError(_("The country detected for this VAT number does not match the one set on this Tax unit."))

            if not checked_country_code:
                error_label = _("tax unit [%s]", record.name)
                error_message = self.env['res.partner']._build_vat_error_message(record.country_id.code.lower(), record.vat, error_label)
                raise ValidationError(error_message)
