from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import formatLang

_debug = DebugLog(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _name = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    advance_payment_method = fields.Selection(
        selection=[
            ("delivered", "Regular invoice"),
            ("percentage", "Down payment (percentage)"),
            ("fixed", "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default="delivered",
        required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing,"
        "according to their invoicing policy (based on ordered or delivered quantity).",
    )
    count = fields.Count(
        count_of="sale_order_ids",
        string="Order Count",
    )
    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        default=lambda self: self.env.context.get("active_ids"),
    )

    has_down_payments = fields.Boolean(
        string="Has down payments",
        compute="_compute_has_down_payments",
    )
    deduct_down_payments = fields.Boolean(
        string="Deduct down payments",
        default=True,
    )

    amount = fields.Float(
        string="Down Payment",
        help="The percentage of amount to be invoiced in advance.",
    )
    fixed_amount = fields.Monetary(
        string="Down Payment Amount (Fixed)",
        help="The fixed amount to be invoiced in advance.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Already invoiced",
        compute="_compute_amount_taxinc_invoiced",
        help="Only confirmed down payments are considered.",
    )

    display_draft_invoice_warning = fields.Boolean(
        compute="_compute_display_draft_invoice_warning"
    )
    consolidated_billing = fields.Boolean(
        default=True,
        help="Create one invoice for all orders related to same customer, same invoicing address"
        " and same delivery address.",
    )

    @api.depends("sale_order_ids")
    def _compute_has_down_payments(self):
        for wizard in self:
            wizard.has_down_payments = bool(
                wizard.sale_order_ids.line_ids.filtered("is_downpayment")
            )

    @api.depends("sale_order_ids")
    def _compute_currency_id(self):
        self.currency_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.currency_id = wizard.sale_order_ids.currency_id

    @api.depends("sale_order_ids")
    def _compute_company_id(self):
        self.company_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.company_id = wizard.sale_order_ids.company_id

    @api.depends("sale_order_ids")
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            invoice_states = wizard.sale_order_ids._origin.sudo().invoice_ids.mapped(
                "state"
            )
            wizard.display_draft_invoice_warning = "draft" in invoice_states

    @api.depends("sale_order_ids")
    def _compute_amount_taxinc_invoiced(self):
        for wizard in self:
            wizard.amount_taxinc_invoiced = sum(
                wizard.sale_order_ids._origin.mapped("amount_taxinc_invoiced")
            )

    @api.onchange("advance_payment_method")
    def _onchange_advance_payment_method(self):
        if self.advance_payment_method == "percentage":
            amount = self.default_get(["amount"]).get("amount")
            return {"value": {"amount": amount}}
        return None

    def _check_amount_is_positive(self):
        for wizard in self:
            if (
                wizard.advance_payment_method == "percentage" and wizard.amount <= 0.00
            ) or (
                wizard.advance_payment_method == "fixed" and wizard.fixed_amount <= 0.00
            ):
                _debug.logic(
                    "down_payment_amount_rejected",
                    wizard=wizard,
                    method=wizard.advance_payment_method,
                    reason="not_positive",
                )
                raise UserError(
                    _("The value of the down payment amount must be positive.")
                )
            if wizard.advance_payment_method == "percentage" and wizard.amount > 100.0:
                _debug.logic(
                    "down_payment_amount_rejected",
                    wizard=wizard,
                    method=wizard.advance_payment_method,
                    reason="over_100_percent",
                )
                raise UserError(
                    _("The percentage of the down payment cannot exceed 100%.")
                )

    def create_invoices(self):
        self._check_amount_is_positive()
        invoices = self._create_invoices(self.sale_order_ids)
        _debug.lifecycle(
            "advance_invoices_created",
            wizard=self,
            orders=self.sale_order_ids,
            invoices=invoices,
        )
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def view_draft_invoices(self):
        return {
            "name": _("Draft Invoices"),
            "type": "ir.actions.act_window",
            "view_mode": "list",
            "views": [(False, "list"), (False, "form")],
            "res_model": "account.move",
            "domain": [
                ("line_ids.sale_line_ids.order_id", "in", self.sale_order_ids.ids),
                ("state", "=", "draft"),
            ],
        }

    def _create_invoices(self, sale_orders):
        self.check_singleton()
        if self.advance_payment_method == "delivered":
            _debug.pipeline(
                "invoice_wizard",
                wizard=self,
                method="delivered",
                orders=sale_orders,
                deduct=self.deduct_down_payments,
                consolidated=self.consolidated_billing,
            )
            return sale_orders._create_invoices(
                final=self.deduct_down_payments, grouped=not self.consolidated_billing
            )
        else:
            self.sale_order_ids.check_singleton()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            AccountTax = self.env["account.tax"]
            order_lines = order.line_ids.filtered(lambda x: not x.display_type)
            base_lines = [
                line._prepare_base_line_for_taxes_computation() for line in order_lines
            ]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            if self.advance_payment_method == "percentage":
                amount_type = "percent"
                amount = self.amount
            else:
                amount_type = "fixed"
                amount = self.fixed_amount

            _debug.pipeline(
                "down_payment_base_lines",
                wizard=self,
                order=order,
                lines=order_lines,
                amount_type=amount_type,
                amount=amount,
            )
            down_payment_base_lines = AccountTax._prepare_down_payment_lines(
                base_lines=base_lines,
                company=self.company_id,
                amount_type=amount_type,
                amount=amount,
                computation_key=f"down_payment,{self.id}",
            )

            order._create_down_payment_section_line_if_needed()
            so_lines = order._create_down_payment_lines_from_base_lines(
                down_payment_base_lines
            )

            invoice_values = self.with_context(
                accounts=[
                    base_line["account_id"]
                    or self._get_down_payment_account(base_line["product_id"])
                    for base_line in down_payment_base_lines
                ],
            )._prepare_down_payment_invoice_values(
                order=order,
                so_lines=so_lines,
            )
            invoice_sudo = self.env["account.move"].sudo().create(invoice_values)
            _debug.lifecycle(
                "down_payment_invoice_created",
                order=order,
                invoice=invoice_sudo,
                so_lines=so_lines,
            )

            invoice = invoice_sudo.sudo(self.env.su)
            poster = (self.env.user._is_internal() and self.env.user.id) or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                "mail.message_origin_link",
                render_values={"self": invoice, "origin": order},
                subtype_xmlid="mail.mt_note",
            )

            title = _("Down payment invoice")
            order.with_user(poster).message_post(
                body=_("%s has been created", invoice._get_html_link(title=title)),
            )

            return invoice

    def _prepare_down_payment_invoice_values(self, order, so_lines):
        self.check_singleton()
        accounts = self.env.context.get("accounts")
        return {
            **order._prepare_invoice_vals(),
            "invoice_line_ids": [
                Command.create(
                    self._prepare_down_payment_invoice_line_values(
                        order,
                        so_line,
                        self.company_id.downpayment_account_id or account,
                    )
                )
                for so_line, account in zip(so_lines, accounts, strict=True)
            ],
        }

    def _prepare_down_payment_invoice_line_values(self, order, so_line, account):
        self.check_singleton()
        self = self.with_context(lang=order._get_lang())

        if self.advance_payment_method == "percentage":
            name = self.env._("Down payment of %s%%", formatLang(self.env, self.amount))
        else:
            name = self.env._("Down Payment")

        return so_line._prepare_aml_vals(
            name=name,
            quantity=1.0,
            **({"account_id": account.id} if account else {}),
        )

    def _get_down_payment_account(self, product):
        product_account = product.product_tmpl_id._get_product_accounts(
            fiscal_pos=self.sale_order_ids.fiscal_position_id
        )
        _debug.logic(
            "down_payment_account",
            product=product,
            by="downpayment" if product_account.get("downpayment") else "income",
        )
        return product_account.get("downpayment") or product_account.get("income")
