from collections import defaultdict

from odoo import fields, models
from odoo.tools import float_round
from odoo.tools.float_utils import float_repr


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_th_tax_invoice_ids = fields.One2many(
        string="Tax Invoices",
        comodel_name='l10n_th.tax.invoice',
        inverse_name='invoice_move_id',
    )
    l10n_th_is_vat_registered = fields.Boolean(related='company_id.l10n_th_is_vat_registered')

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'TH':
            return 'l10n_th.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_th_get_credit_debit_note_amounts(self):
        self.ensure_one()

        if original_move := self.reversed_entry_id:
            related_moves = original_move.reversal_move_ids
            sign = -1
        elif 'debit_origin_id' in self._fields and (original_move := self.debit_origin_id):
            related_moves = original_move.debit_note_ids
            sign = 1
        else:
            return []

        previous_amount = sum(
            related_moves.filtered(
                lambda move: (
                    move.state == 'posted'
                    and (
                        move._get_accounting_date_source() < self._get_accounting_date_source()
                        or (
                            move._get_accounting_date_source() == self._get_accounting_date_source()
                            and (not self.name or self.name == '/' or move.name < self.name)
                        )
                    )
                ),
            ).mapped('amount_untaxed'),
        )

        original_amount = original_move.amount_untaxed + sign * previous_amount
        corrected_amount = original_amount + sign * self.amount_untaxed

        return [
            {
                'label': self.env._("Original Amount"),
                'amount': original_amount,
            },
            {
                'label': self.env._("Correct Amount"),
                'amount': corrected_amount,
            },
        ]

    def _get_th_moves(self):
        return self.filtered(
            lambda move: (
                move.move_type in {'out_invoice', 'out_receipt'}
                and move.country_code == 'TH'
                and move.l10n_th_is_vat_registered
            ),
        )

    def _get_th_caba_entries(self):
        return self.filtered(
            lambda entry: (
                entry.tax_cash_basis_origin_move_id
                and entry.country_code == 'TH'
                and entry.l10n_th_is_vat_registered
            ),
        )

    def _get_exigible_invoice_lines(self, tax_exigibility):
        """Return the product invoice lines that have at least one non-withholding
        tax with the specified tax exigibility."""

        self.ensure_one()

        return self.invoice_line_ids.filtered(
            lambda line: (
                line.display_type == "product"
                and any(
                    not tax.is_withholding_tax
                    and (
                        tax.tax_exigibility == tax_exigibility
                        if tax.amount_type != "group"
                        else any(
                            child_tax.tax_exigibility == tax_exigibility
                            for child_tax in tax.children_tax_ids
                        )
                    )
                    for tax in line.tax_ids
                )
            ),
        )

    def _get_th_tax_invoice_base_lines(self, lines):
        """
        Prepare and compute the tax details of the given invoice lines, excluding
        withholding taxes.
        A per-exigibility filter will be done later on, as filtering too early would
        bring problems for moves mixing both "on invoice" and "on payment" taxes in a
        single tax group.
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        base_lines = [
            AccountTax._prepare_base_line_for_taxes_computation(line, filter_tax_function=lambda t: not t.is_withholding_tax)
            for line in lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        return base_lines

    def _get_th_tax_invoice_totals(self, base_lines, tax_exigibility):
        """
        Aggregate the tax amounts of the given base lines per tax group, keeping only the taxes
        matching the given tax exigibility.
        The base lines provided when calling this should come from `_get_th_tax_invoice_base_lines`
        and should have already been rounded.
        """
        tax_group_amounts = defaultdict()
        total_excluded = total_tax_amount = 0.0
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            total_excluded += tax_details['total_excluded_currency']
            for tax_data in tax_details['taxes_data']:
                if tax_data['tax'].tax_exigibility != tax_exigibility:
                    continue
                tax_group = tax_data['tax'].tax_group_id
                tax_group_amounts.setdefault(
                    tax_group.id,
                    {
                        "group_name": tax_group.name,
                        "amount": 0.0,
                    },
                )
                tax_group_amounts[tax_group.id]['amount'] += tax_data['tax_amount_currency']
                total_tax_amount += tax_data['tax_amount_currency']
        return {
            'total_amount': total_excluded + total_tax_amount,
            'vat_amount': total_tax_amount,
            'tax_group_amounts': list(tax_group_amounts.values()),
        }

    def _get_th_tax_invoice_line_data(self, base_lines, tax_exigibility):
        """Return a list of dictionaries containing the required data for the given
        invoice base_lines, formatted for use in the Thai tax invoice. The total amount
        is based on the specified document tax mode."""
        self.ensure_one()
        dp = self.currency_id.decimal_places
        tax_invoice_lines = []
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            exigible_tax_amount = sum(
                tax_data['tax_amount_currency']
                for tax_data in tax_details['taxes_data']
                if tax_data['tax'].tax_exigibility == tax_exigibility
            )
            total_excluded = tax_details['total_excluded_currency']
            tax_invoice_lines.append({
                "name": base_line['record'].name,
                "quantity": float_repr(base_line['product_uom_id']._compute_quantity(base_line['quantity'], base_line['product_id'].uom_id), precision_digits=2),
                "product_uom": base_line['product_uom_id'].display_name,
                "price_unit": float_repr(float_round(base_line['price_unit'], precision_digits=dp), precision_digits=dp),
                "discount": float_repr(base_line['discount'], precision_digits=2) if base_line['discount'] else '',
                "taxes": ", ".join(filter(None, base_line['tax_ids'].mapped('tax_label'))),
                "total_amount": (
                    total_excluded
                    if self.document_tax_mode == "tax_excluded"
                    else total_excluded + exigible_tax_amount
                ),
            })
        return tax_invoice_lines

    def _update_or_create_l10n_th_tax_invoice(self):
        """Create or update tax invoices using invoice lines with on-invoice tax exigibility."""

        tax_invoice_vals = []

        for move in self:
            invoice_exigible_lines = move._get_exigible_invoice_lines(
                tax_exigibility="on_invoice",
            )

            # On-invoice tax invoices have no reference, with at most one active invoice.
            tax_invoice = move.l10n_th_tax_invoice_ids.filtered(
                lambda tax_invoice: not tax_invoice.reference
                    and tax_invoice.state != 'cancel',
            )[:1]

            if not invoice_exigible_lines:
                tax_invoice.state = 'cancel'
                continue

            base_lines = move._get_th_tax_invoice_base_lines(invoice_exigible_lines)
            tax_totals = move._get_th_tax_invoice_totals(base_lines, tax_exigibility='on_invoice')

            tax_invoice_val = {
                'invoice_move_id': move.id,
                'date': move.invoice_date,
                'total_amount': tax_totals['total_amount'],
                'vat_amount': tax_totals['vat_amount'],
                'tax_group_amounts': tax_totals['tax_group_amounts'],
                'tax_invoice_lines': move._get_th_tax_invoice_line_data(
                    base_lines,
                    tax_exigibility='on_invoice',
                ),
            }

            if tax_invoice:
                tax_invoice.write(tax_invoice_val)
            else:
                tax_invoice_vals.append(tax_invoice_val)

        self.env['l10n_th.tax.invoice'].create(tax_invoice_vals)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Cancel all tax invoices linked to CABA entries that are being reversed."""

        th_caba_entries = self._get_th_caba_entries()

        self.env['l10n_th.tax.invoice'].search([
            ('payment_move_id', 'in', th_caba_entries.ids),
            ('state', '!=', 'cancel'),
        ]).state = 'cancel'

        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def unlink(self):
        """Cancel all tax invoices linked to CABA entries that are going to be deleted."""

        th_caba_entries = self._get_th_caba_entries()

        if not th_caba_entries:
            return super().unlink()

        tax_invoices = self.env['l10n_th.tax.invoice'].search([
            ('payment_move_id', 'in', th_caba_entries.ids),
            ('state', '!=', 'cancel'),
        ])
        tax_invoices.state = 'cancel'

        return super().unlink()

    def _post(self, soft=True):
        """Create or update the tax invoice for posted Thai VAT-registered customer invoices."""

        res = super()._post(soft=soft)

        th_vat_registered_moves = self.filtered(
            lambda move: (
                move.move_type in {'out_invoice', 'out_receipt'}
                and move.state == 'posted'
                and move.country_code == 'TH'
                and move.l10n_th_is_vat_registered
            ),
        )

        th_vat_registered_moves._update_or_create_l10n_th_tax_invoice()

        th_vat_registered_moves.l10n_th_tax_invoice_ids.filtered(
            lambda tax_invoice: tax_invoice.state == 'draft',
        ).state = 'posted'

        return res

    def button_draft(self):
        th_moves = self._get_th_moves()

        th_moves.l10n_th_tax_invoice_ids.filtered(
            lambda tax_invoice: tax_invoice.state == 'posted',
        ).state = 'draft'

        return super().button_draft()

    def button_cancel(self):
        th_moves = self._get_th_moves()

        th_moves.l10n_th_tax_invoice_ids.filtered(
            lambda tax_invoice: tax_invoice.state != 'cancel',
        ).state = 'cancel'

        return super().button_cancel()
