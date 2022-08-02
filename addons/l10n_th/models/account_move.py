# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_th_get_debit_note_tax_difference(self):
        # get total sum of taxes for tax group: VAT 7%
        vat_tax_group_name = self.env.ref('l10n_th.tax_group_vat_7').name
        tax_groups = [tax_group for subtotal_tax in self.tax_totals['groups_by_subtotal'].values() for tax_group in subtotal_tax]
        filtered_tax_groups = list(filter(lambda tax_group: tax_group['tax_group_name'] == vat_tax_group_name, tax_groups))
        tax_sum = sum([tax_group['tax_group_amount'] for tax_group in filtered_tax_groups])
        return tax_sum
