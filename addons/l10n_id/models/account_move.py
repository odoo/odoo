# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_tax_totals(self):
        """ OVERRIDE

        For invoices based on ID company as of January 2025, there is a separate tax base computation for non-luxury goods.
        Tax base is supposed to be 11/12 of original while tax amount is increased from 11% to 12% hence effectively
        maintaining 11% tax amount.

        We change tax totals section to display adjusted base amount on invoice PDF for special non-luxury goods tax group.
        """
        super()._compute_tax_totals()
        for move in self.filtered(lambda m: m.is_sale_document()):
            # invoice might be coming from different companies, each tax group with unique XML ID
            non_luxury_tax_group = self.env['account.chart.template'].with_company(move.company_id.id).ref("l10n_id_tax_group_non_luxury_goods", raise_if_not_found=False)
            if not non_luxury_tax_group or move.invoice_date and move.invoice_date < fields.Date.to_date('2025-01-01'):
                continue
            for subtotal_group in move.tax_totals['groups_by_subtotal'].values():
                for group in subtotal_group:
                    if group['tax_group_id'] == non_luxury_tax_group.id:
                        dpp = group['tax_group_base_amount'] * (11 / 12)
                        # adding (DPP) information to make it clearer for users why the number is different from the Untaxed Amount
                        group.update({
                            'tax_group_base_amount': dpp,
                            'formatted_tax_group_base_amount': formatLang(self.env, dpp, currency_obj=move.currency_id),
                            'tax_group_name': group['tax_group_name'] + ' (on DPP)',
                        })
                        move.tax_totals['display_tax_base'] = True
