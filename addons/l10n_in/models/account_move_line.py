from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_tds_tcs_section = fields.Many2one(related="account_id.l10n_in_tds_tcs_section")
    l10n_in_line_warning = fields.Boolean()

    @api.depends('product_id', 'product_id.l10n_in_hsn_code')
    def _compute_l10n_in_hsn_code(self):
        for line in self:
            if line.move_id.country_code == 'IN' and line.parent_state == 'draft':
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def _l10n_in_get_line_amount(self):
        self.ensure_one()
        if self.move_id.move_type == 'out_invoice':
            return self.credit or -self.debit
        elif self.move_id.move_type == 'in_invoice':
            return -self.credit or self.debit
        else:
            return self.credit or self.debit

    def _l10n_in_compute_tcs_tds_line_warning(self, warning_sections):
        tax_group = self.l10n_in_tds_tcs_section
        res = True
        if tax_group.l10n_in_per_transaction_units == 'per_unit':
            res = (
                tax_group.l10n_in_is_per_transaction_limit
                and self._l10n_in_compute_price_total(is_aggregate=False) > tax_group.l10n_in_per_transaction_limit
            )
        elif tax_group not in warning_sections:
            res = any(
                tax_group in l.l10n_in_tds_tcs_section
                and not l.company_currency_id.is_zero(l._l10n_in_get_line_amount())
                and tax_group in l.tax_ids.mapped('tax_group_id')
                for l in self.move_id.invoice_line_ids
            )
        return res and self.move_id._l10n_in_is_warning_applicable(tax_group)

    def _l10n_in_compute_price_total(self, is_aggregate=True):
        self.ensure_one()
        tax_group_id = self.l10n_in_tds_tcs_section
        transaction_amount = self._l10n_in_get_line_amount()
        if self.tax_ids and tax_group_id.l10n_in_consider_tax == 'total_amount':
            computed_values = self.tax_ids.compute_all(transaction_amount)
            transaction_amount = computed_values['total_included']
        if not is_aggregate and tax_group_id.l10n_in_per_transaction_units == 'per_unit':
            return transaction_amount / self.quantity
        return transaction_amount
