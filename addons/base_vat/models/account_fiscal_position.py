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
