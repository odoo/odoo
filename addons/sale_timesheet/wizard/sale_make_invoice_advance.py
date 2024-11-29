# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    date_start_invoice_timesheet = fields.Date(
        string="Start Date",
        help="Only timesheets not yet invoiced (and validated, if applicable) from this period will be invoiced. If the period is not indicated, all timesheets not yet invoiced (and validated, if applicable) will be invoiced without distinction.")
    date_end_invoice_timesheet = fields.Date(
        string="End Date",
        help="Only timesheets not yet invoiced (and validated, if applicable) from this period will be invoiced. If the period is not indicated, all timesheets not yet invoiced (and validated, if applicable) will be invoiced without distinction.")
    invoicing_timesheet_enabled = fields.Boolean(compute='_compute_invoicing_timesheet_enabled', store=True, export_string_translation=False)

    #=== COMPUTE METHODS ===#

    @api.depends('sale_order_ids')
    def _compute_invoicing_timesheet_enabled(self):
        for wizard in self:
            wizard.invoicing_timesheet_enabled = bool(
                wizard.sale_order_ids.order_line.filtered(
                    lambda sol: sol.invoice_status == 'to invoice'
                ).product_id.filtered(
                    lambda p: p._is_delivered_timesheet()
                )
            )

    #=== BUSINESS METHODS ===#

    def _create_invoices(self, sale_orders):
        """ Override method from sale/wizard/sale_make_invoice_advance.py

            When the user want to invoice the timesheets to the SO
            up to a specific period then we need to recompute the
            qty_to_invoice for each product_id in sale.order.line,
            before creating the invoice.
        """
        if self.advance_payment_method == 'delivered' and self.invoicing_timesheet_enabled:
            if self.date_start_invoice_timesheet or self.date_end_invoice_timesheet:
                sale_orders.order_line._recompute_qty_to_invoice(
                    self.date_start_invoice_timesheet, self.date_end_invoice_timesheet)

            return sale_orders.with_context(
                timesheet_start_date=self.date_start_invoice_timesheet,
                timesheet_end_date=self.date_end_invoice_timesheet
            )._create_invoices(final=self.deduct_down_payments, grouped=not self.consolidated_billing)

        return super()._create_invoices(sale_orders)
