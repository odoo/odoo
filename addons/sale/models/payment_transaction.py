from datetime import datetime

from dateutil import relativedelta

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import str2bool
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="sale_order_transaction_rel",
        column1="transaction_id",
        column2="sale_order_id",
        string="Sales Orders",
        copy=False,
        readonly=True,
    )
    sale_order_ids_nbr = fields.Count(
        count_of="sale_order_ids",
        string="# of Sales Orders",
    )

    @api.model
    def _get_reference_prefix(self, separator, **values):
        command_list = values.get("sale_order_ids")
        if command_list:
            order_ids = self._fields["sale_order_ids"].convert_to_cache(
                command_list, self
            )
            orders = self.env["sale.order"].browse(order_ids).exists()
            if len(orders) == len(order_ids):
                _debug.logic("reference_prefix", by="sale_orders", orders=orders)
                return separator.join(orders.mapped("name"))
        return super()._get_reference_prefix(separator, **values)

    def _get_sale_order_reference(self, order):
        self.check_singleton()
        if self.provider_id.so_reference_type == "so_name":
            order_reference = order.name
        elif self.provider_id.so_reference_type == "partner":
            identification_number = order.partner_id.id
            order_reference = "%s/%s" % (
                "CUST",
                str(identification_number % 97).rjust(2, "0"),
            )
        else:
            order_reference = False

        _debug.logic(
            "sale_order_reference",
            transaction=self,
            order=order,
            by=self.provider_id.so_reference_type,
        )
        invoice_journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.company_id.id)], limit=1
        )
        if invoice_journal:
            order_reference = invoice_journal._process_reference_for_sale_order(
                order_reference
            )

        return order_reference

    def _post_process(self):
        _debug.pipeline("tx_post_process", transactions=self)
        for pending_tx in self.filtered(lambda tx: tx.state == "pending"):
            super(PaymentTransaction, pending_tx)._post_process()
            sales_orders = pending_tx.sale_order_ids.filtered(
                lambda so: so.state == "draft"
            )
            sales_orders.filtered(lambda so: not so.sent).with_context(
                tracking_disable=True
            ).action_quotation_sent()

            if pending_tx.provider_id.code == "custom":
                for order in pending_tx.sale_order_ids:
                    order.reference = pending_tx._get_sale_order_reference(order)

            if pending_tx.operation == "validation":
                continue
            sales_orders._send_mail_order_payment_succeeded()

        for authorized_tx in self.filtered(lambda tx: tx.state == "authorized"):
            super(PaymentTransaction, authorized_tx)._post_process()
            confirmed_orders = authorized_tx._confirm_orders_if_amount_reached()
            if authorized_tx.operation == "validation":
                continue
            if remaining_orders := (authorized_tx.sale_order_ids - confirmed_orders):
                remaining_orders._send_mail_order_payment_succeeded()

        super(
            PaymentTransaction,
            self.filtered(lambda tx: tx.state not in ["pending", "authorized", "done"]),
        )._post_process()

        done_txs = self.filtered(lambda tx: tx.state == "done")
        params = self.env["ir.config_parameter"].sudo()
        auto_invoice = bool(done_txs) and str2bool(
            params.get_param("sale.automatic_invoice"),
        )
        async_emails = auto_invoice and str2bool(
            params.get_param("sale.async_emails"),
        )
        _debug.logic(
            "tx_done_policy",
            transactions=done_txs,
            auto_invoice=auto_invoice,
            async_emails=async_emails,
        )
        for done_tx in done_txs:
            if done_tx.operation != "validation":
                confirmed_orders = done_tx._confirm_orders_if_amount_reached()
                (
                    done_tx.sale_order_ids - confirmed_orders
                )._send_mail_order_payment_succeeded()
            if auto_invoice:
                done_tx._invoice_sale_orders()
            super(PaymentTransaction, done_tx)._post_process()
            if auto_invoice and not self.env.context.get("skip_sale_auto_invoice_send"):
                if async_emails and (
                    send_invoice_cron := self.env.ref(
                        "sale.send_invoice_cron", raise_if_not_found=False
                    )
                ):
                    _debug.lifecycle("invoice_send_deferred", transaction=done_tx)
                    send_invoice_cron._trigger()
                else:
                    self._send_invoice()

    def _confirm_orders_if_amount_reached(self):
        confirmed_orders = self.env["sale.order"]
        for tx in self:
            if len(tx.sale_order_ids) == 1:
                quotation = tx.sale_order_ids.filtered(lambda so: so.state == "draft")
                if (
                    quotation
                    and not quotation._has_to_be_signed()
                    and quotation._is_confirmation_amount_reached()
                ):
                    _debug.lifecycle(
                        "order_confirmed_by_payment", transaction=tx, order=quotation
                    )
                    quotation.with_context(
                        send_email=True, sale_include_signature=True
                    ).action_confirm()
                    confirmed_orders |= quotation
        _debug.pipeline(
            "confirm_orders_if_amount_reached",
            transactions=self,
            confirmed=confirmed_orders,
        )
        return confirmed_orders

    def _log_message_on_linked_documents(self, message):
        super()._log_message_on_linked_documents(message)
        if self.env.uid == SUPERUSER_ID or self.env.context.get(
            "payment_backend_action"
        ):
            author = self.env.user.partner_id
        else:
            author = self.partner_id
        for order in self.sale_order_ids or self.source_transaction_id.sale_order_ids:
            order.message_post(body=message, author_id=author.id)

    def _send_invoice(self):
        for tx in self.with_user(SUPERUSER_ID):
            tx = tx.with_company(tx.company_id).with_context(
                company_id=tx.company_id.id,
            )
            invoice_to_send = tx.invoice_ids.filtered(
                lambda i: (
                    not i.is_move_sent
                    and i.state == "posted"
                    and i._is_ready_to_be_sent()
                )
            )
            send_context = {"allow_raising": False, "allow_fallback_pdf": True}
            default_template_param = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("sale.default_invoice_email_template", False)
            )
            if default_template_param:
                mail_template = (
                    self.env["mail.template"].sudo().browse(int(default_template_param))
                )
                if mail_template.exists():
                    send_context["mail_template"] = mail_template

            _debug.pipeline(
                "tx_send_invoices", transaction=tx, invoices=invoice_to_send
            )
            tx.env["mixin.account.move.send"]._generate_and_send_invoices(
                invoice_to_send,
                **send_context,
            )

    def _cron_send_invoice(self):
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale.automatic_invoice")
        ):
            _debug.logic("cron_send_invoice_skipped", reason="automatic_invoice_off")
            return

        retry_limit_date = datetime.now() - relativedelta.relativedelta(days=2)
        self.search(
            [
                ("state", "=", "done"),
                ("is_post_processed", "=", True),
                (
                    "invoice_ids",
                    "in",
                    self.env["account.move"]._search(
                        [
                            ("is_move_sent", "=", False),
                            ("state", "=", "posted"),
                        ]
                    ),
                ),
                ("sale_order_ids.state", "=", "done"),
                ("last_state_change", ">=", retry_limit_date),
            ]
        )._send_invoice()

    def _invoice_sale_orders(self):
        for tx in self.filtered(lambda tx: tx.sale_order_ids):
            tx = tx.with_company(tx.company_id)

            confirmed_orders = tx.sale_order_ids.filtered(lambda so: so.state == "done")
            if confirmed_orders:
                fully_paid_orders = confirmed_orders.filtered(lambda so: so._is_paid())

                downpayment_invoices = (
                    confirmed_orders - fully_paid_orders
                )._generate_downpayment_invoices()

                fully_paid_orders._force_lines_to_invoice_policy_order()
                final_invoices = fully_paid_orders.with_context(
                    raise_if_nothing_to_invoice=False
                )._create_invoices(final=True)
                invoices = downpayment_invoices + final_invoices

                for invoice in invoices:
                    invoice._portal_get_or_create_token()
                _debug.pipeline(
                    "tx_invoice_sale_orders",
                    transaction=tx,
                    confirmed=confirmed_orders,
                    fully_paid=fully_paid_orders,
                    invoices=invoices,
                )
                if invoices:
                    tx.invoice_ids = [Command.set(invoices.ids)]

    @api.readonly
    def action_view_sales_orders(self):
        action = {
            "name": _("Sales Order(s)"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "target": "current",
        }
        sale_order_ids = self.sale_order_ids.ids
        if len(sale_order_ids) == 1:
            action["res_id"] = sale_order_ids[0]
            action["view_mode"] = "form"
        else:
            action["view_mode"] = "list,form"
            action["domain"] = [("id", "in", sale_order_ids)]
        return action
