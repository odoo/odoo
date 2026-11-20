from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ge_treaty_exempt_amount = fields.Monetary(
        string="Withheld Treaty Exempt",
        currency_field='company_currency_id',
        compute='_compute_l10n_ge_treaty_exempt_amount',
        store=True,
        help="Treaty exempt amount of the withholding lines behind this withholding tax journal item,"
        " in company currency and signed like its base amount.",
    )

    @api.depends('tax_repartition_line_id', 'analytic_distribution', 'move_id.origin_payment_id.withholding_line_ids.l10n_ge_treaty_exempt_amount', 'move_id.reversed_entry_id.origin_payment_id.withholding_line_ids.l10n_ge_treaty_exempt_amount')
    def _compute_l10n_ge_treaty_exempt_amount(self):
        # Read from the payment's withholding lines: account._sync_tax_lines may replace this tax line on reset to draft.
        AccountTax = self.env['account.tax']
        treaty_amounts_per_payment = {}
        for line in self:
            payment = line.move_id.origin_payment_id or line.move_id.reversed_entry_id.origin_payment_id
            sign = 1 if line.move_id.origin_payment_id else -1
            if not line.tax_repartition_line_id or not payment.withholding_line_ids:
                line.l10n_ge_treaty_exempt_amount = 0.0
                continue
            if payment not in treaty_amounts_per_payment:
                treaty_amounts_per_payment[payment] = payment.withholding_line_ids._l10n_ge_get_treaty_exempt_amounts()
            line_grouping_key = AccountTax._prepare_tax_line_repartition_grouping_key(AccountTax._prepare_tax_line_for_taxes_computation(line))
            line.l10n_ge_treaty_exempt_amount = sign * sum(amount for grouping_key, amount in treaty_amounts_per_payment[payment] if all(line_grouping_key.get(field) == value for field, value in grouping_key.items()))

    @api.constrains('tax_ids')
    def _check_l10n_ge_gross_withholding_tax_alone(self):
        for line in self:
            withholding_taxes = line.tax_ids.filtered('is_withholding_tax')
            if len(withholding_taxes) > 1 and any(withholding_taxes.mapped('l10n_ge_is_gross')):
                raise ValidationError(self.env._("A gross withholding tax cannot be combined with another withholding tax on the same line."))
