from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_residual = fields.Monetary(
        help="The total amount due, including the amount to be paid and the withholding due."
    )
    withholding_total_amount_currency = fields.Monetary(
        compute="_compute_withholding_total_amount",
        store=True,
        currency_field='currency_id',
        help="The total withholding amount to be deducted."
    )
    withholding_deducted_amount_currency = fields.Monetary(
        compute="_compute_deducted_withholding_amount",
        store=True,
        currency_field='currency_id',
        help="The total withholding amount already deducted."
    )
    withholding_residual_amount_currency = fields.Monetary(
        compute="_compute_residual_withholding_amount",
        currency_field='currency_id',
        help="The remaining withholding amount to be deducted."
    )
    withholding_net_residual_amount_currency = fields.Monetary(
        string="Net Due Amount",
        compute="_compute_withholding_net_residual_amount",
        currency_field="currency_id",
        help="The net amount due after deducting the remaining withholding amount."
    )

    @api.depends("line_ids.tax_ids", "line_ids.price_unit", "line_ids.quantity", "line_ids.discount")
    def _compute_withholding_total_amount(self):
        AccountTax = self.env["account.tax"]

        for move in self:
            withholding_total_amount_currency = 0.0

            if move.is_invoice(include_receipts=True):
                for line in move.line_ids.filtered(lambda l: l.tax_ids):
                    withholding_taxes = line.tax_ids.filtered(lambda t: t.is_withholding_tax)
                    if not withholding_taxes:
                        continue
                    base_line = AccountTax._prepare_base_line_for_taxes_computation(
                        line,
                        tax_ids=withholding_taxes,
                        price_unit=line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                        quantity=line.quantity,
                        currency_id=move.currency_id,
                        calculate_withholding_taxes=True,
                    )

                    AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
                    AccountTax._round_base_lines_tax_details([base_line], move.company_id)
                    tax_details = base_line.get("tax_details", {})
                    taxes_data = tax_details.get("taxes_data", [])

                    for tax_data in taxes_data:
                        tax = tax_data.get("tax")
                        if tax and tax.is_withholding_tax:
                            withholding_total_amount_currency += tax_data.get("tax_amount_currency", 0.0)

            move.withholding_total_amount_currency = move.currency_id.round(-withholding_total_amount_currency)

    @api.depends("withholding_total_amount_currency", "line_ids.matched_debit_ids", "line_ids.matched_credit_ids")
    def _compute_deducted_withholding_amount(self):
        for move in self:
            withholding_deducted_currency = 0.0
            if move.is_invoice(include_receipts=True):
                for line in move.line_ids.filtered(lambda l: l.display_type == 'payment_term'):
                    partial_fname, counterpart_line_fname, amount_fname = (
                        ('matched_credit_ids', 'credit_move_id', 'credit_amount_currency')
                        if line.debit else
                        ('matched_debit_ids', 'debit_move_id', 'debit_amount_currency')
                    )
                    for counterpart_move, partials in line[partial_fname].grouped(lambda p: p[counterpart_line_fname].move_id).items():
                        ratio = sum(
                            partial[amount_fname] / counterpart_amount
                            for partial in partials
                            if (counterpart_amount := partial[counterpart_line_fname].amount_currency)
                        )
                        withholding_deducted_currency += sum(
                            wth_line.currency_id._convert(
                                from_amount=-wth_line.amount_currency * ratio,
                                to_currency=move.currency_id,
                                company=move.company_id,
                                date=counterpart_move.date,
                                round=False,
                            )
                            for wth_line in counterpart_move.line_ids.filtered('tax_line_id.is_withholding_tax')
                        )
            move.withholding_deducted_amount_currency = withholding_deducted_currency

    @api.depends("withholding_total_amount_currency", "withholding_deducted_amount_currency")
    def _compute_residual_withholding_amount(self):
        for move in self:
            move.withholding_residual_amount_currency = move.withholding_total_amount_currency - move.withholding_deducted_amount_currency

    @api.depends("amount_residual", "withholding_residual_amount_currency")
    def _compute_withholding_net_residual_amount(self):
        for move in self:
            if move.withholding_residual_amount_currency > 0:
                move.withholding_net_residual_amount_currency = move.amount_residual - move.withholding_residual_amount_currency
            else:
                move.withholding_net_residual_amount_currency = move.amount_residual

    def _prepare_payments_widget_reconciled_info(self, partial_info):
        res = super()._prepare_payments_widget_reconciled_info(partial_info)
        res['is_withhold'] = bool(partial_info['aml'].move_id.is_withhold_entry())
        return res

    def is_withhold_entry(self):
        self.ensure_one()
        return (
            self.move_type == 'entry'
            and self.origin_payment_id.withhold == 'withhold'
        )
