from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_date

_debug = DebugLog(__name__)

AUTO_STATEMENT_PROCESSING_BATCH_SIZE = 100


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    cron_last_check = fields.Datetime()
    debit = fields.Monetary(
        compute="_compute_debit_credit",
        inverse="_inverse_debit",
    )
    credit = fields.Monetary(
        compute="_compute_debit_credit",
        inverse="_inverse_credit",
    )
    bank_statement_attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        compute="_compute_bank_statement_attachment_ids",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        related="move_id.attachment_ids",
    )

    @_debug.perf.timed
    def action_save_close(self):
        _debug.lifecycle("action_save_close", records=self)
        return {"type": "ir.actions.act_window_close"}

    @_debug.perf.timed
    def action_save_new(self):
        _debug.lifecycle("action_save_new", records=self)
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_bank_statement_line_form_bank_rec_widget"
        )
        action["context"] = {
            "default_journal_id": self.env.context["default_journal_id"]
        }
        return action

    @_debug.perf.timed
    def action_button_draft(self):
        _debug.lifecycle("action_button_draft", records=self)
        return self.move_id.action_draft()

    @api.depends("statement_id")
    @_debug.perf.timed
    def _compute_bank_statement_attachment_ids(self):
        attachments = (
            self.env["ir.attachment"]
            .search(
                [
                    ("res_model", "=", "account.bank.statement"),
                    ("res_id", "in", self.statement_id.ids),
                    ("res_field", "in", (False, "invoice_pdf_report_file")),
                ]
            )
            .grouped("res_id")
        )

        for st_line in self:
            st_line.bank_statement_attachment_ids = attachments.get(
                st_line.statement_id.id
            )

    @api.model
    @_debug.perf.timed
    def _action_view_bank_reconciliation_widget(
        self, extra_domain=None, default_context=None, name=None, kanban_first=True
    ):
        _debug.lifecycle("_action_view_bank_reconciliation_widget", records=self)
        if default_context is None:
            default_context = {}
        action_reference = "account.action_bank_statement_line_transactions" + (
            "_kanban" if kanban_first else ""
        )
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            action_reference
        )

        default_journal = self.env["account.journal"].browse(
            default_context.get(
                "default_journal_id", default_context.get("search_default_journal_id")
            )
        )

        _debug.logic(
            "widget_action_resolved",
            action_reference=action_reference,
            journal=default_journal,
            extra_domain=bool(extra_domain),
        )
        action.update(
            {
                "name": name or _("Bank Matching"),
                "context": {
                    **default_context,
                    "bank_statements_source": default_journal.exists().bank_statements_source,
                    "auto_statement_processing": True,
                },
                "domain": [("state", "!=", "cancel")] + (extra_domain or []),
            }
        )

        return action

    @_debug.perf.timed
    def action_view_recon_st_line(self):
        _debug.lifecycle("action_view_recon_st_line", records=self)
        self.check_singleton()
        return self.env[
            "account.bank.statement.line"
        ]._action_view_bank_reconciliation_widget(
            name=self.name,
            default_context={
                "default_statement_id": self.statement_id.id,
                "default_journal_id": self.journal_id.id,
                "default_st_line_id": self.id,
                "search_default_id": self.id,
            },
        )

    _PARTNER_MATCH_RANKS = {
        "bank_account": (
            "account_matching_partner_with_company",
            "account_matching_partner_without_company",
        ),
        "partner_name": (
            "full_name_matching_partner_with_company",
            "full_name_matching_partner_without_company",
            "partial_name_matching_partner_with_company",
            "partial_name_matching_partner_without_company",
        ),
    }

    def create_document_from_attachment(self, attachment_ids):
        statement_line = self.browse(self.env.context.get("statement_line_id"))

        purchase_journal_id = self.env["account.journal"].search_fetch(
            domain=[
                *self.env["account.journal"]._check_company_domain(
                    statement_line.company_id
                ),
                ("type", "=", "purchase"),
            ],
            field_names=["id"],
            limit=1,
        )
        invoices = purchase_journal_id.with_context(
            default_move_type="in_invoice"
        )._create_document_from_attachment(attachment_ids)
        if lines := invoices.line_ids.filtered(
            lambda l: (
                l.account_id.account_type in {"asset_receivable", "liability_payable"}
            )
        ):
            statement_line.set_line_bank_statement_line(lines.ids)
            invoices.action_activate_currency()

        return invoices._get_records_action()

    @_debug.perf.timed
    def action_unreconcile_entry(self):
        _debug.lifecycle("action_unreconcile_entry", records=self)
        self.check_singleton()

        _liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()
        other_lines.remove_move_reconcile()

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        statement_lines = super().create(vals_list)
        if not self.env.context.get("no_retrieve_partner"):
            statement_lines._set_partner_from_transaction()
        statement_lines.move_id._message_log_batch(
            bodies={
                statement_line.move_id.id: statement_line._format_statement_line_data()
                for statement_line in statement_lines
            }
        )

        if self.env.context.get("auto_statement_processing", False) and statement_lines:
            _debug.pipeline(
                "auto_statement_processing_batches",
                stline=statement_lines,
                auto_statement_processing_batch_size=AUTO_STATEMENT_PROCESSING_BATCH_SIZE,
            )
            for index in range(
                0, len(statement_lines), AUTO_STATEMENT_PROCESSING_BATCH_SIZE
            ):
                statement_lines[
                    index : index + AUTO_STATEMENT_PROCESSING_BATCH_SIZE
                ]._try_auto_reconcile_statement_lines()
        return statement_lines

    @api.deprecated("Use _format_statement_line_data instead")
    def _format_transaction_details(self):
        return self._format_statement_line_data()

    @_debug.perf.timed
    def _format_statement_line_data(self):
        def _get_formatted_transaction_details(data, prefix=""):
            keys = (
                data.keys()
                if isinstance(data, dict)
                else [i for i, _ in enumerate(data)]
            )
            result = Markup()
            for key in keys:
                value = data[key]
                result += prefix + Markup("<b>%s:</b> ") % str(key)
                if isinstance(value, (list, dict)):
                    result += "\n"
                    result += _get_formatted_transaction_details(value, prefix + "  ")
                    continue
                result += str(value) + "\n"
            return result

        def _get_formatted_statement_line_data():
            result = Markup()
            if self.partner_name or self.partner_id or self.account_number:
                result += Markup(
                    '<h4 class="d-inline">{name}</h4> <span class="text-secondary">―</span> '
                ).format(
                    name=self.partner_name
                    or self.partner_id.name
                    or self.account_number,
                )
            result += Markup(
                '<h4 class="d-inline text-info">{amount}</h4><br/>'
            ).format(amount=self.currency_id.format(self.amount))
            if self.account_number and (self.partner_name or self.partner_id):
                result += Markup(
                    '<b>{account_number}</b> <span class="text-secondary">-</span> '
                ).format(account_number=self.account_number)
            result += Markup("{date}<br/>").format(
                date=format_date(self.env, self.date, date_format="dd MMM yyyy")
            )
            result += Markup("<br/>{remittance_information}<br/>").format(
                remittance_information=self.payment_ref
            )
            return result

        self.check_singleton()

        formatted_statement_line_data = _get_formatted_statement_line_data()
        if self.transaction_details:
            formatted_statement_line_data = Markup(
                '%s<div data-o-mail-quote="1"><pre>%s</pre></div>'
            ) % (
                formatted_statement_line_data,
                _get_formatted_transaction_details(self.transaction_details),
            )
        _debug.logic(
            "statement_line_formatted",
            stline=self,
            with_transaction_details=bool(self.transaction_details),
        )
        return formatted_statement_line_data

    @api.depends("amount")
    def _compute_debit_credit(self):
        for line in self:
            line.debit = -line.amount if line.amount < 0.0 else 0.0
            line.credit = max(0.0, line.amount)

    @api.onchange("debit")
    def _inverse_debit(self):
        for line in self:
            if line.debit:
                line.credit = 0
            if line.debit != line._origin.debit:
                line.amount = line.credit - line.debit

    @api.onchange("credit")
    def _inverse_credit(self):
        for line in self:
            if line.credit:
                line.debit = 0
            if line.credit != line._origin.credit:
                line.amount = line.credit - line.debit
