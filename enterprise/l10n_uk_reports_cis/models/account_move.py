from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_uk_cis_wrong_taxes = fields.Boolean(compute='_compute_l10n_uk_cis_wrong_taxes')
    l10n_uk_cis_inactive_partner = fields.Boolean(compute='_compute_l10n_uk_cis_inactive_partner', store=True)

    @api.depends('partner_id', 'invoice_line_ids.tax_ids', 'partner_id.l10n_uk_reports_cis_deduction_rate', 'l10n_uk_cis_inactive_partner')
    def _compute_l10n_uk_cis_wrong_taxes(self):
        purchase_tax_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase_expr_deduction')._get_matching_tags()

        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') or move.company_id.country_code != 'GB' or move.l10n_uk_cis_inactive_partner or not move.partner_id:
                move.l10n_uk_cis_wrong_taxes = False
            else:
                move_percentage_taxes = move.invoice_line_ids.tax_ids.filtered(
                    lambda tax: tax.amount_type == 'percent'
                    and float_compare(tax.amount, move.partner_id.commercial_partner_id._get_deduction_amount_from_rate(), precision_digits=0) != 0
                )

                move.l10n_uk_cis_wrong_taxes = set(move_percentage_taxes.repartition_line_ids.tag_ids.ids) & set(purchase_tax_tags.ids)

    @api.depends('partner_id', 'invoice_line_ids.tax_ids', 'partner_id.commercial_partner_id.l10n_uk_cis_enabled')
    def _compute_l10n_uk_cis_inactive_partner(self):
        purchase_tax_tags = self.env['account.account.tag']
        if expr := self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase_expr_deduction', raise_if_not_found=False):
            purchase_tax_tags = expr._get_matching_tags()

        for move in self:
            if move.move_type in ('out_refund', 'out_invoice') or move.company_id.country_code != 'GB' or move.partner_id.commercial_partner_id.l10n_uk_cis_enabled:
                move.l10n_uk_cis_inactive_partner = False
            else:
                move.l10n_uk_cis_inactive_partner = set(purchase_tax_tags.ids) & set(move.invoice_line_ids.tax_ids.invoice_repartition_line_ids.tag_ids.ids)

    def l10n_uk_reports_cis_action_open_commercial_partner(self):
        self.ensure_one()
        return {
            'view_mode': 'form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'res_id': self.partner_id.commercial_partner_id.id,
            'views': [(False, 'form')],
        }
