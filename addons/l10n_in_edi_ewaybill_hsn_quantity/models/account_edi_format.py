# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        res = super()._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
        res['quantity'] = line.hsn_quantity
        return res
