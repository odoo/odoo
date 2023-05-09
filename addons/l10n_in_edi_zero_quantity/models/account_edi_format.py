# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class AccountEDIFormat(models.Model):
    _inherit = "account.edi.format"

    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details):
        item_lines_json = super()._get_l10n_in_edi_line_details(index, line, line_tax_details)
        if line.l10n_in_edi_is_zero_quantity:
            item_lines_json["Qty"] = 0
        return item_lines_json

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        item_lines_json = super()._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
        if line.l10n_in_edi_is_zero_quantity:
            item_lines_json['quantity'] = 0
        return item_lines_json
