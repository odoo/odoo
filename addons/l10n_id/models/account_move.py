# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.misc import formatLang

class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_tax_totals(self):
        """ OVERRIDE

        For invoices based on ID company as of January 2025, there is a separate tax base computation for nun-luxury goods.
        Tax base is supposed to be 11/12 of original while other tax bases should remain the same.

        To avoid affecting calculation of total amount, set tax_group_amount to 0 but the formatted_tax_group_amount to
        the DPP value
        """
        super()._compute_tax_totals()
        dpp_label = "DPP Other Value (11 / 12)"
        for move in self:
            non_luxury_tax_group_id = self.env.ref('l10n_id.l10n_id_tax_group_non_luxury_goods', raise_if_not_found=False).id
            if move.country_code == "ID" and move.invoice_date and move.invoice_date >= fields.Date.to_date("2025-01-01"):
                dpp_other_value = 0
                # for non-luxury taxes, accumulate total adjusted base amount
                for subtotal in move.tax_totals['groups_by_subtotal']:
                    subtotal_group = move.tax_totals['groups_by_subtotal'][subtotal]
                    for group in subtotal_group:
                        # For components with the non-luxury tax group, adjust the base amount for `formatted_tax_group_base_amount`
                        # to avoid changing the total calculation
                        if group['tax_group_id'] == non_luxury_tax_group_id:
                            dpp = group['tax_group_base_amount'] * (11 / 12)
                            dpp_other_value += dpp
                            group['formatted_tax_group_base_amount'] = formatLang(self.env, dpp, currency_obj=move.currency_id)
                if dpp_other_value > 0:
                    label = move.tax_totals['subtotals_order'][0]
                    group = move.tax_totals['groups_by_subtotal']
                    dpp_group = {
                        "tax_group_name": dpp_label,
                        "tax_group_amount": 0,
                        "tax_group_base_amount": 0,
                        "formatted_tax_group_amount": formatLang(self.env, dpp_other_value, currency_obj=move.currency_id),
                        "formatted_tax_group_base_amount": 0,
                        "dpp_amount": dpp_other_value,
                        "hide_base_amount": True,
                    }
                    group[label] = [dpp_group] + group[label]
