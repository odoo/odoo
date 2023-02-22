# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_th_get_debit_note_tax_difference(self):
        # get total sum of taxes for tax group: VAT 7%
        self.ensure_one()

        tax_group = self.env.ref('l10n_th.tax_group_vat_7', raise_if_not_found=False)
        if not tax_group:
            raise UserError("Tax group VAT 7% not found!")
        vat_tax_group_name = tax_group.name
        tax_sum = 0
        for tax_group_list in self.tax_totals['groups_by_subtotal'].values():
            for tax_group in tax_group_list:
                if tax_group['tax_group_name'] == vat_tax_group_name:
                    tax_sum += tax_group['tax_group_amount']
        return tax_sum
