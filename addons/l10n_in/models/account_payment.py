from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # withholding related fields
    l10n_in_withhold_move_ids = fields.One2many(
        'account.move', 'l10n_in_withholding_ref_payment_id',
        string="Indian Payment TDS Entries",
    )
    l10n_in_total_withholding_amount = fields.Monetary(compute='_compute_l10n_in_total_withholding_amount')
    l10n_in_tds_feature_enabled = fields.Boolean(related='company_id.l10n_in_tds_feature')

    def _compute_l10n_in_total_withholding_amount(self):
        for payment in self:
            if payment.company_id.l10n_in_tds_feature:
                payment.l10n_in_total_withholding_amount = sum(payment.l10n_in_withhold_move_ids.filtered(
                    lambda m: m.state == 'posted').l10n_in_withholding_line_ids.mapped('l10n_in_withhold_tax_amount'))
            else:
                payment.l10n_in_total_withholding_amount = 0.0

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }
