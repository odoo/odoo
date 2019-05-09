# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    l10n_latam_price_unit = fields.Monetary(
        string='Unit Price',
        compute='_compute_l10n_latam_prices_and_taxes'
    )
    l10n_latam_price_subtotal = fields.Monetary(
        string='Amount',
        compute='_compute_report_prices_and_taxes'
    )
    l10n_latam_price_net = fields.Monetary(
        string='Net Amount',
        compute='_compute_report_prices_and_taxes'
    )
    l10n_latam_invoice_line_tax_ids = fields.One2many(
        string='Taxes',
        compute="_compute_report_prices_and_taxes",
        comodel_name='account.tax',
    )

    @api.depends(
        'price_unit', 'price_subtotal',
        'invoice_id.l10n_latam_document_type_id')
    def _compute_l10n_latam_prices_and_taxes(self):
        for line in self:
            invoice = line.invoice_id
            taxes_included = (
                invoice.l10n_latam_document_type_id and
                invoice.l10n_latam_document_type_id.get_taxes_included() or False)
            if not taxes_included:
                report_price_unit = line.price_unit
                report_price_subtotal = line.price_subtotal
                not_included_taxes = line.invoice_line_tax_ids
                report_price_net = report_price_unit * (
                    1 - (line.discount or 0.0) / 100.0)
            else:
                included_taxes = line.invoice_line_tax_ids.filtered(
                    lambda x: x in taxes_included)
                not_included_taxes = (
                    line.invoice_line_tax_ids - included_taxes)
                report_price_unit = included_taxes.compute_all(
                    line.price_unit, invoice.currency_id, 1.0, line.product_id,
                    invoice.partner_id)['total_included']
                report_price_net = report_price_unit * (
                    1 - (line.discount or 0.0) / 100.0)
                report_price_subtotal = report_price_net * line.quantity
            line.report_price_subtotal = report_price_subtotal
            line.report_price_unit = report_price_unit
            line.report_price_net = report_price_net
            line.report_invoice_line_tax_ids = not_included_taxes
