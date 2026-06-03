# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sg_permit_number = fields.Char(string="Permit No.")

    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")

    l10n_sg_customer_accounting_gst_amount = fields.Monetary(
        compute='_compute_l10n_sg_customer_accounting_gst_amount',
        currency_field='company_currency_id',
    )

    def _get_name_invoice_report(self):
        self.ensure_one()
        # In SG, GST-registered companies (i.e. with a `vat`) will issue a "tax invoice".
        if self.company_id.account_fiscal_country_id.code == 'SG' and self.company_id.vat:
            return 'l10n_sg.report_invoice_document'
        return super()._get_name_invoice_report()

    @api.depends('move_type', 'invoice_line_ids.display_type', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids.ubl_cii_tax_category_code')
    def _compute_l10n_sg_customer_accounting_gst_amount(self):
        """Compute the Customer Accounting GST amount for SRCA-S lines.

        Under Singapore's Customer Accounting scheme, the supplier issues a 0% tax invoice
        but must indicate the GST amount the customer is required to account for to IRAS.
        """
        AccountTax = self.env['account.tax']
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                move.l10n_sg_customer_accounting_gst_amount = 0.0
                continue

            srca_s_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product' and any(
                    t.ubl_cii_tax_category_code == 'SRCA-S' for t in l.tax_ids
                )
            )
            sales_tax = move.company_id.account_sale_tax_id
            if not srca_s_lines or not sales_tax:
                move.l10n_sg_customer_accounting_gst_amount = 0.0
                continue

            # Compute GST using the standard sales tax rate on SRCA-S line amounts
            base_lines = [{
                **move._prepare_product_base_line_for_taxes_computation(line),
                'tax_ids': sales_tax,
            } for line in srca_s_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, move.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, move.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=move.currency_id,
                company=move.company_id,
                cash_rounding=move.invoice_cash_rounding_id,
            )
            move.l10n_sg_customer_accounting_gst_amount = tax_totals['tax_amount']
