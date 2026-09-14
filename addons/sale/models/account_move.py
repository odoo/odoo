from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "mixin.utm"]

    campaign_id = fields.Many2one(ondelete="set null")
    medium_id = fields.Many2one(ondelete="set null")
    source_id = fields.Many2one(ondelete="set null")

    sale_order_count = fields.Integer(
        compute="_compute_sale_order_count",
        compute_sudo=True,
    )
    sale_warning_text = fields.Text(
        string="Sale Warning",
        compute="_compute_sale_warning_text",
        depends_context=("uid",),
        help="Internal warning for the partner or the products as set by the user.",
    )
    sale_customer_invoice_id = fields.Many2one(
        comodel_name="sale.invoice.match",
        string="Sales Auto-complete",
        store=False,
        readonly=False,
        help="Auto-complete from a previous invoice, credit note, or sales order.",
    )
    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        store=False,
        readonly=False,
        help="Auto-complete from a past sales order.",
    )
    sale_order_name = fields.Char(compute="_compute_sale_order_name")
    is_sale_matched = fields.Boolean(
        compute="_compute_is_sale_matched",
        help="0: SO not required or partially linked. 1: All lines linked",
    )

    def unlink(self):
        own_lines = self.line_ids
        downpayment_lines = own_lines.sale_line_ids.filtered(
            lambda line: line.is_downpayment and line.invoice_line_ids <= own_lines,
        )
        res = super().unlink()
        if downpayment_lines:
            _debug.lifecycle("downpayment_lines_unlinked", lines=downpayment_lines)
            downpayment_lines.unlink()
        return res

    @api.depends("move_type", "partner_id")
    def _compute_invoice_user_id(self):
        super()._compute_invoice_user_id()
        for move in self:
            if move.is_sale_document(include_receipts=True):
                if not move.invoice_user_id or move.invoice_user_id == self.env.user:
                    move.invoice_user_id = (
                        move.partner_id.user_id
                        or move.partner_id.commercial_partner_id.user_id
                        or self.env.user
                    )

    @api.depends("line_ids.sale_line_ids")
    def _compute_sale_order_count(self):
        for move in self:
            move.sale_order_count = len(move.line_ids.sale_line_ids.order_id)

    @api.depends("line_ids.sale_line_ids")
    def _compute_is_sale_matched(self):
        for move in self:
            move.is_sale_matched = not any(
                line.display_type == "product" and not line.sale_line_ids
                for line in move.invoice_line_ids
            )

    @api.depends(
        "sale_order_count",
        "invoice_line_ids.sale_line_ids.order_id.display_name",
    )
    def _compute_sale_order_name(self):
        for move in self:
            if move.sale_order_count == 1:
                move.sale_order_name = (
                    move.invoice_line_ids.sale_line_ids.order_id.display_name
                )
            else:
                move.sale_order_name = False

    @api.onchange("sale_customer_invoice_id", "sale_id")
    def _onchange_sale_auto_complete(self):
        if self.sale_customer_invoice_id.move_id:
            self.invoice_vendor_bill_id = self.sale_customer_invoice_id.move_id
            self._onchange_invoice_vendor_bill()
        elif self.sale_customer_invoice_id.order_id:
            self.sale_id = self.sale_customer_invoice_id.order_id
        self.sale_customer_invoice_id = False

        if not self.sale_id:
            _debug.logic("sale_auto_complete_skipped", reason="no_order")
            return

        invoice_vals = self.sale_id.with_company(
            self.sale_id.company_id,
        )._prepare_invoice_vals()
        has_invoice_lines = bool(
            self.invoice_line_ids.filtered(
                lambda line: (
                    line.display_type
                    not in ("line_section", "line_subsection", "line_note")
                ),
            ),
        )
        new_currency_id = (
            self.currency_id if has_invoice_lines else invoice_vals.get("currency_id")
        )
        del invoice_vals["company_id"]
        if self.move_type == invoice_vals["move_type"]:
            del invoice_vals["move_type"]
        self.update(invoice_vals)
        self.currency_id = new_currency_id

        order_lines = self.sale_id.line_ids - self.invoice_line_ids.mapped(
            "sale_line_ids",
        )
        _debug.pipeline(
            "sale_auto_complete",
            move=self._origin,
            order=self.sale_id,
            added_lines=order_lines,
            had_lines=has_invoice_lines,
        )
        self._add_order_lines(order_lines)

        origins = set(self.invoice_line_ids.mapped("sale_line_ids.order_id.name"))
        self.invoice_origin = ",".join(list(origins))

        if self.company_id != self.sale_id.company_id:
            self.company_id = self.sale_id.company_id

        self.sale_id = False

    def action_sale_matching(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sale Matching"),
            "res_model": "sale.invoice.line.match",
            "domain": [
                (
                    "partner_id",
                    "in",
                    (self.partner_id | self.partner_id.commercial_partner_id).ids,
                ),
                ("company_id", "in", self.env.companies.ids),
                ("company_id", "child_of", self.company_id.ids),
                ("account_move_id", "in", [self.id, False]),
            ],
            "views": [
                (self.env.ref("sale.sale_invoice_line_match_list").id, "list"),
            ],
        }

    @api.depends(
        "partner_id.name",
        "partner_id.sale_warn_msg",
        "partner_id.parent_id.name",
        "partner_id.parent_id.sale_warn_msg",
        "invoice_line_ids.product_id.sale_line_warn_msg",
        "invoice_line_ids.product_id.display_name",
    )
    def _compute_sale_warning_text(self):
        if not self.env.user.has_group("sale.group_warning_sale"):
            self.sale_warning_text = ""
            _debug.logic("sale_warnings_skipped", reason="no_warning_group")
            return
        for move in self:
            if move.move_type != "out_invoice":
                move.sale_warning_text = ""
                continue
            warnings = OrderedSet()
            if partner_msg := move.partner_id.sale_warn_msg:
                warnings.add(
                    (move.partner_id.name or move.partner_id.display_name)
                    + " - "
                    + partner_msg,
                )
            if partner_parent_msg := move.partner_id.parent_id.sale_warn_msg:
                parent = move.partner_id.parent_id
                warnings.add(
                    (parent.name or parent.display_name) + " - " + partner_parent_msg
                )
            for product in move.invoice_line_ids.product_id:
                if product_msg := product.sale_line_warn_msg:
                    warnings.add(product.display_name + " - " + product_msg)
            move.sale_warning_text = "\n".join(warnings)

    def action_cancel(self):
        res = super().action_cancel()
        self.line_ids.filtered("is_downpayment").sale_line_ids.filtered(
            lambda line: not line.display_type,
        )._compute_name()
        return res

    def action_draft(self):
        res = super().action_draft()

        self.line_ids.filtered("is_downpayment").sale_line_ids.filtered(
            lambda line: not line.display_type,
        )._compute_name()

        return res

    def _action_invoice_ready_to_be_sent(self):
        res = super()._action_invoice_ready_to_be_sent()

        send_invoice_cron = self.env.ref(
            "sale.send_invoice_cron",
            raise_if_not_found=False,
        )
        if send_invoice_cron:
            _debug.lifecycle("invoice_send_cron_triggered", moves=self)
            send_invoice_cron._trigger()

        return res

    def action_post(self):
        res = super().action_post()

        dp_lines = self.line_ids.sale_line_ids.filtered(
            lambda line: line.is_downpayment and not line.display_type,
        )
        dp_lines._compute_name()
        downpayment_lines = dp_lines.filtered(lambda line: not line.order_id.locked)
        other_so_lines = downpayment_lines.order_id.line_ids - downpayment_lines
        real_invoices = set(other_so_lines.invoice_line_ids.move_id)
        _debug.pipeline(
            "downpayment_lines_repriced",
            moves=self,
            lines=downpayment_lines,
            real_invoices=len(real_invoices),
        )
        for so_dpl in downpayment_lines:
            so_dpl.price_unit = so_dpl._get_downpayment_price_unit(real_invoices)
            so_dpl.tax_ids = so_dpl.invoice_line_ids.tax_ids

        return res

    def action_view_source_sale_orders(self):
        self.check_singleton()
        source_orders = self.line_ids.sale_line_ids.order_id
        result = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "sale.action_sale_order"
        )
        if len(source_orders) > 1:
            result["domain"] = [("id", "in", source_orders.ids)]
        elif len(source_orders) == 1:
            result["views"] = [(self.env.ref("sale.view_sale_order_form").id, "form")]
            result["res_id"] = source_orders.id
        else:
            result = {"type": "ir.actions.act_window_close"}
        return result

    def create_sale_order(self):
        self.check_singleton()
        if any(not line.product_id for line in self.invoice_line_ids):
            _debug.logic(
                "create_sale_order_refused", move=self, reason="line_no_product"
            )
            raise UserError(
                self.env._(
                    "Some move lines does not have a product set. Please review",
                ),
            )

        sale_exist = self.env["sale.order"].search(
            [
                ("partner_id", "=", self.commercial_partner_id.id),
                ("company_id", "=", self.company_id.id),
                ("origin", "=", self.name),
            ],
        )
        if len(sale_exist) > 1:
            _debug.logic(
                "create_sale_order_refused",
                move=self,
                reason="ambiguous_origin",
                orders=sale_exist,
            )
            raise UserError(
                self.env._(
                    "More than one Sale Orders with the same origin have been found."
                    " Please review",
                ),
            )

        if sale_exist:
            _debug.logic("create_sale_order_reused", move=self, order=sale_exist)
            return sale_exist

        sale = self.env["sale.order"].create(self._prepare_sale_order_vals())
        _debug.lifecycle("sale_order_created_from_move", move=self, order=sale)
        for move_line_id, vals in self._prepare_sale_line_vals(sale).items():
            move_line = self.env["account.move.line"].browse(move_line_id)
            move_line.sale_line_ids = self.env["sale.order.line"].create(vals)
        return sale

    def _post_entries(self):
        posted = super()._post_entries()

        for invoice in posted.filtered(lambda move: move.is_invoice()):
            payments = invoice.mapped("transaction_ids.payment_id").filtered(
                lambda x: x.state == "in_process",
            )
            move_lines = payments.move_id.line_ids.filtered(
                lambda line: (
                    line.account_type in ("asset_receivable", "liability_payable")
                    and not line.reconciled
                ),
            )
            _debug.pipeline("outstanding_lines_added", move=invoice, lines=move_lines)
            for line in move_lines:
                invoice.js_add_outstanding_line(line.id)
        return posted

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]
        default_values_list = [
            {
                **default_values,
                "campaign_id": move.campaign_id.id,
                "medium_id": move.medium_id.id,
                "source_id": move.source_id.id,
            }
            for move, default_values in zip(self, default_values_list, strict=True)
        ]
        return super()._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel,
        )

    def _invoice_paid_hook(self):
        res = super()._invoice_paid_hook()
        todo = set()
        for invoice in self.filtered(lambda move: move.is_invoice()):
            for line in invoice.invoice_line_ids:
                todo.update(
                    (sale_line.order_id, invoice.name)
                    for sale_line in line.sale_line_ids
                )
        _debug.pipeline("invoice_paid_hook", moves=self, orders_notified=len(todo))
        for order, name in todo:
            order.message_post(body=_("Invoice %s paid", name))
        return res

    def _get_sale_order_invoiced_amount(self, order):
        order_amount = 0
        for invoice in self:
            prices = sum(
                invoice.line_ids.filtered(
                    lambda x: (
                        x.display_type
                        not in ("line_note", "line_section", "line_subsection")
                        and order in x.sale_line_ids.order_id
                    ),
                ).mapped("price_total"),
            )
            order_amount += invoice.currency_id._convert(
                prices * -invoice.direction_sign,
                order.currency_id,
                invoice.company_id,
                invoice.invoice_date or invoice.date or fields.Date.context_today(self),
            )
        return order_amount

    def _get_partner_credit_warning_exclude_amount(self):
        exclude_amount = super()._get_partner_credit_warning_exclude_amount()
        for order in self.line_ids.sale_line_ids.order_id:
            order_amount = min(
                self._get_sale_order_invoiced_amount(order),
                order.amount_taxinc_to_invoice,
            )
            order_amount_company = order.currency_id._convert(
                max(order_amount, 0),
                self.company_id.currency_id,
                self.company_id,
                fields.Date.context_today(self),
            )
            exclude_amount += order_amount_company
            _debug.logic(
                "credit_warning_excluded",
                move=self,
                order=order,
                amount=order_amount_company,
            )
        return exclude_amount

    def _is_downpayment(self):
        self.check_singleton()
        return (
            self.line_ids.sale_line_ids
            and all(
                sale_line.is_downpayment for sale_line in self.line_ids.sale_line_ids
            )
        ) or False

    def _prepare_sale_order_vals(self) -> dict:
        self.check_singleton()
        return {
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "partner_id": self.commercial_partner_id.id,
            "date_order": self.invoice_date,
            "fiscal_position_id": (
                self.fiscal_position_id
                or self.env["account.fiscal.position"]._get_fiscal_position(
                    self.commercial_partner_id,
                )
            ).id,
            "payment_term_id": self.invoice_payment_term_id.id,
            "origin": self.name,
            "invoice_state": "done",
        }

    def _prepare_sale_line_vals(self, sale) -> dict:
        self.check_singleton()
        sale_line_vals = {}
        fpos = sale.fiscal_position_id
        company_domain = self.env["account.tax"]._check_company_domain(self.company_id)
        for line in self.invoice_line_ids.filtered(
            lambda ln: ln.display_type == "product",
        ):
            taxes = fpos.map_tax(line.product_id.sudo().taxes_id)
            if taxes:
                taxes = taxes.filtered_domain(company_domain)
            sale_line_vals[line.id] = {
                "order_id": sale.id,
                "product_id": line.product_id.id,
                "name": (
                    f"[{line.product_id.default_code}] {line.name}"
                    if line.product_id.default_code
                    else line.name
                ),
                "product_qty": line.quantity,
                "product_uom_id": line.product_uom_id.id,
                "price_unit": line.price_unit,
                "tax_ids": [Command.set(taxes.ids)],
                "analytic_distribution": line.analytic_distribution,
            }
        return sale_line_vals
