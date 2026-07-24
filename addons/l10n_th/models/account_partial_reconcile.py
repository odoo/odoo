from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def _create_tax_cash_basis_moves(self):
        res = super()._create_tax_cash_basis_moves()

        th_cash_basis_entries = res.filtered(
            lambda entry: (
                entry.country_code == 'TH'
                and entry.l10n_th_is_vat_registered
                and entry.tax_cash_basis_origin_move_id.move_type in {'out_invoice', 'out_receipt'}
            ),
        )

        self._create_l10n_th_tax_invoices_from_caba_entries(
            th_cash_basis_entries,
        )

        return res

    def _create_l10n_th_tax_invoices_from_caba_entries(self, entries):
        """Create Thai tax invoices for the given CABA entries."""
        tax_invoice_vals = []

        for entry in entries:
            original_move = entry.tax_cash_basis_origin_move_id
            payment_exigible_lines = original_move._get_exigible_invoice_lines('on_payment')
            payment_exigible_base_lines = original_move._get_th_tax_invoice_base_lines(payment_exigible_lines)
            tax_group_amounts = {}
            tax_amount = 0.0

            for line in entry.line_ids.filtered('tax_line_id'):
                tax_group = line.tax_line_id.tax_group_id
                tax_group_amounts.setdefault(
                    tax_group.id,
                    {
                        'group_name': tax_group.name,
                        'amount': 0.0,
                    },
                )
                tax_group_amounts[tax_group.id]['amount'] += abs(line.amount_currency)
                tax_amount += abs(line.amount_currency)

            tax_invoice_vals.append({
                'invoice_move_id': original_move.id,
                'payment_move_id': entry.id,
                'reference': entry.name,
                'date': entry.date,
                'total_amount': entry.amount_total_in_currency_signed,
                'vat_amount': tax_amount,
                'amount_residual': original_move.amount_residual,
                'tax_group_amounts': list(tax_group_amounts.values()),
                'tax_invoice_lines': original_move._get_th_tax_invoice_line_data(
                    payment_exigible_base_lines,
                    tax_exigibility='on_payment',
                ),
                'state': 'posted',
            })

        self.env['l10n_th.tax.invoice'].create(tax_invoice_vals)
