from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinOrderAmount(models.AbstractModel):
    _name = "mixin.order.amount"
    _description = "Order Amount Computation"

    currency_id = fields.Many2one(comodel_name="res.currency")

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    tax_totals = fields.Binary(
        compute="_compute_tax_totals",
        exportable=False,
    )

    amount_taxexc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Excl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Incl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance (Tax Excl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxinc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance (Tax Incl.)",
        compute="_compute_amounts_invoice",
    )

    partner_credit_warning = fields.Text(compute="_compute_partner_credit_warning")

    def _prepare_tax_totals_data(self):
        self.check_singleton()
        AccountTax = self.env["account.tax"]
        order_lines = self.line_ids.filtered(lambda line: not line.display_type)
        base_lines = [
            line._prepare_base_line_for_taxes_computation() for line in order_lines
        ]
        base_lines += self._get_additional_base_lines()
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        _debug.perf.count(
            "tax_totals_data", order=self, lines=len(order_lines), base=len(base_lines)
        )
        return AccountTax._get_tax_totals_summary(
            base_lines=base_lines,
            currency=self.currency_id or self.company_id.currency_id,
            company=self.company_id,
        )

    def _get_additional_base_lines(self):
        return []

    @api.depends_context("lang")
    @api.depends(
        "company_id",
        "currency_id",
        "payment_term_id",
        "line_ids.price_subtotal",
    )
    def _compute_tax_totals(self):
        for order in self:
            order.tax_totals = order._prepare_tax_totals_data()

    @api.depends("tax_totals")
    def _compute_amounts(self):
        for order in self:
            tax_totals = order.tax_totals
            order.amount_untaxed = tax_totals["base_amount_currency"]
            order.amount_tax = tax_totals["tax_amount_currency"]
            order.amount_total = tax_totals["total_amount_currency"]
            _debug.logic(
                "order_amounts",
                order=order,
                untaxed=order.amount_untaxed,
                tax=order.amount_tax,
                total=order.amount_total,
            )

    @api.depends(
        "line_ids.amount_taxexc_invoiced",
        "line_ids.amount_taxexc_to_invoice",
        "line_ids.amount_taxinc_invoiced",
        "line_ids.amount_taxinc_to_invoice",
    )
    def _compute_amounts_invoice(self):
        for order in self:
            taxexc_invoiced = 0.0
            taxexc_to_invoice = 0.0
            taxinc_invoiced = 0.0
            taxinc_to_invoice = 0.0

            for line in order.line_ids:
                taxexc_invoiced += line.amount_taxexc_invoiced
                taxexc_to_invoice += line.amount_taxexc_to_invoice
                taxinc_invoiced += line.amount_taxinc_invoiced
                taxinc_to_invoice += line.amount_taxinc_to_invoice

            order.amount_taxexc_invoiced = taxexc_invoiced
            order.amount_taxexc_to_invoice = taxexc_to_invoice
            order.amount_taxinc_invoiced = taxinc_invoiced
            order.amount_taxinc_to_invoice = taxinc_to_invoice

    @api.depends("company_id", "partner_id", "amount_total")
    def _compute_partner_credit_warning(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.partner_credit_warning = ""
            show_warning = (
                order.state == "draft" and order.company_id.account_use_credit_limit
            )
            _debug.logic("credit_warning_checked", order=order, show=bool(show_warning))
            if show_warning:
                order.partner_credit_warning = self.env[
                    "account.move"
                ]._prepare_credit_warning_message(
                    order.sudo(),
                    current_amount=(order.amount_total / (order.currency_rate or 1.0)),
                )
