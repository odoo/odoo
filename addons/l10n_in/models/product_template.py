# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", help="Harmonized System Nomenclature/Services Accounting Code")
    l10n_in_hsn_description = fields.Char(string="HSN/SAC Description", help="HSN/SAC description is required if HSN/SAC code is not provided.")

    @api.constrains('l10n_in_hsn_code')
    def _check_hsn_code_validation(self):
        for record in self:
            company = record.company_id or self.env.company
            minimum_hsn_len = company.l10n_in_hsn_code_digit
            check_hsn = record.l10n_in_hsn_code and minimum_hsn_len
            if check_hsn and len(record.l10n_in_hsn_code) < int(minimum_hsn_len):
                error_message = _("As per your HSN/SAC code validation, minimum %s digits HSN/SAC code is required.", minimum_hsn_len)
                raise ValidationError(error_message)
