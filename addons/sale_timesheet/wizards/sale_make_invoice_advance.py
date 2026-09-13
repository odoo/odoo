from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    date_start_invoice_timesheet = fields.Date(
        string="Start Date",
        help="Only timesheets not yet invoiced (and validated, if applicable) from this period will be invoiced. If the period is not indicated, all timesheets not yet invoiced (and validated, if applicable) will be invoiced without distinction.",
    )
    date_end_invoice_timesheet = fields.Date(
        string="End Date",
        help="Only timesheets not yet invoiced (and validated, if applicable) from this period will be invoiced. If the period is not indicated, all timesheets not yet invoiced (and validated, if applicable) will be invoiced without distinction.",
    )
    invoicing_timesheet_enabled = fields.Boolean(
        export_string_translation=False,
        compute="_compute_invoicing_timesheet_enabled",
        store=True,
    )

    @api.depends("sale_order_ids")
    def _compute_invoicing_timesheet_enabled(self):
        for wizard in self:
            wizard.invoicing_timesheet_enabled = bool(
                wizard.sale_order_ids.line_ids.filtered(
                    lambda sol: sol.invoice_state == "to do"
                ).product_id.filtered(lambda p: p._is_delivered_timesheet())
            )

    def _create_invoices(self, sale_orders):
        if (
            self.advance_payment_method == "delivered"
            and self.invoicing_timesheet_enabled
        ):
            if self.date_start_invoice_timesheet or self.date_end_invoice_timesheet:
                sale_orders.line_ids._recompute_qty_to_invoice(
                    self.date_start_invoice_timesheet, self.date_end_invoice_timesheet
                )

            return sale_orders.with_context(
                timesheet_start_date=self.date_start_invoice_timesheet,
                timesheet_end_date=self.date_end_invoice_timesheet,
            )._create_invoices(
                final=self.deduct_down_payments, grouped=not self.consolidated_billing
            )

        return super()._create_invoices(sale_orders)
