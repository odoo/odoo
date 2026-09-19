import logging
import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.account.models.account_move import BYPASS_LOCK_CHECK

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


_ref_company_registry = {
    "jp": "7000012050002",
    "dk": "58403288",
    "fi": "8763054-9",
}

SEARCH_MODE_RANK_FIELDS = {
    "customer": "customer_rank",
    "supplier": "supplier_rank",
}

ASSET_DIFFERENCE_COMPARISONS = {
    "<": lambda balance, operand: balance < operand,
    "<=": lambda balance, operand: balance <= operand,
    "=": lambda balance, operand: balance == operand,
    "!=": lambda balance, operand: balance != operand,
    ">": lambda balance, operand: balance > operand,
    ">=": lambda balance, operand: balance >= operand,
}
ASSET_DIFFERENCE_NEGATIONS = {
    "<": ">=",
    "<=": ">",
    "=": "!=",
    "!=": "=",
    ">": "<=",
    ">=": "<",
}


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mixin.fiscal.country.codes"]

    def _default_display_invoice_template_pdf_report_id(self):
        reports = self.env[
            "account.move"
        ]._get_available_invoice_template_pdf_report_ids()
        return len(reports) > 1

    fiscal_country_group_codes = fields.Json(
        compute="_compute_fiscal_country_group_codes"
    )
    partner_vat_placeholder = fields.Char(compute="_compute_partner_vat_placeholder")
    duplicate_bank_partner_ids = fields.Many2many(
        related="bank_ids.duplicate_bank_partner_ids"
    )
    name = fields.Char(tracking=True)
    credit = fields.Monetary(
        string="Total Receivable",
        compute="_compute_credit_debit",
        search="_search_credit",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Total amount this customer owes you.",
    )
    credit_to_invoice = fields.Monetary(
        compute="_compute_credit_to_invoice",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    credit_limit = fields.Float(
        copy=False,
        readonly=False,
        company_dependent=True,
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Credit limit specific to this partner.",
    )
    use_partner_credit_limit = fields.Boolean(
        string="Partner Limit",
        compute="_compute_use_partner_credit_limit",
        inverse="_inverse_use_partner_credit_limit",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Set a value greater than 0.0 to activate a credit limit check",
    )
    show_credit_limit = fields.Boolean(
        compute="_compute_show_credit_limit",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    days_sales_outstanding = fields.Float(
        string="Days Sales Outstanding (DSO)",
        compute="_compute_days_sales_outstanding",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="[(Total Receivable/Total Revenue) * number of days since the first invoice] for this customer",
    )
    debit = fields.Monetary(
        string="Total Payable",
        compute="_compute_credit_debit",
        search="_search_debit",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Total amount you have to pay to this vendor.",
    )
    total_invoiced = fields.Monetary(
        compute="_compute_total_invoiced",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        readonly=True,
    )
    property_account_payable_id = fields.Many2one(
        comodel_name="account.account",
        string="Account Payable",
        company_dependent=True,
        domain="[('account_type', '=', 'liability_payable')]",
        ondelete="restrict",
        check_company=True,
    )
    property_account_receivable_id = fields.Many2one(
        comodel_name="account.account",
        string="Account Receivable",
        company_dependent=True,
        domain="[('account_type', '=', 'asset_receivable')]",
        ondelete="restrict",
        check_company=True,
    )
    property_account_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        company_dependent=True,
        check_company=True,
        help="The fiscal position determines the taxes/accounts used for this contact.",
    )
    property_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Customer Payment Terms",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
    )
    property_supplier_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Vendor Payment Terms",
        company_dependent=True,
        check_company=True,
    )
    ref_company_ids = fields.One2many(
        comodel_name="res.company",
        inverse_name="partner_id",
        string="Companies that refers to partner",
    )
    supplier_invoice_count = fields.Integer(
        string="# Vendor Bills",
        compute="_compute_supplier_invoice_count",
    )
    customer_invoice_count = fields.Integer(
        string="# Customer Invoices",
        compute="_compute_customer_invoice_count",
    )
    account_move_count = fields.Integer(
        compute="_compute_account_move_count",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="partner_id",
        string="Invoices",
        copy=False,
        readonly=True,
    )
    contract_ids = fields.One2many(
        comodel_name="account.analytic.account",
        inverse_name="partner_id",
        string="Partner Contracts",
        readonly=True,
    )
    bank_account_count = fields.Count(
        count_of="bank_ids",
        string="Bank",
    )
    trust = fields.Selection(
        selection=[
            ("good", "Good Debtor"),
            ("normal", "Normal Debtor"),
            ("bad", "Bad Debtor"),
        ],
        string="Degree of trust you have in this debtor",
        company_dependent=True,
    )
    ignore_abnormal_invoice_date = fields.Boolean(company_dependent=True)
    ignore_abnormal_invoice_amount = fields.Boolean(company_dependent=True)
    invoice_sending_method = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("email", "by Email"),
        ],
        string="Invoice sending",
        company_dependent=True,
    )
    invoice_edi_format = fields.Selection(
        selection=[],
        string="eInvoice format",
        compute="_compute_invoice_edi_format",
        inverse="_inverse_invoice_edi_format",
        compute_sudo=True,
    )
    invoice_edi_format_store = fields.Char(company_dependent=True)
    display_invoice_edi_format = fields.Boolean(
        default=lambda self: len(self._fields["invoice_edi_format"].selection),
        store=False,
    )
    invoice_template_pdf_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Invoice report",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_invoice_template_pdf_report_ids)]",
    )
    available_invoice_template_pdf_report_ids = fields.One2many(
        comodel_name="ir.actions.report",
        compute="_compute_available_invoice_template_pdf_report_ids",
    )
    display_invoice_template_pdf_report_id = fields.Boolean(
        default=_default_display_invoice_template_pdf_report_id,
        store=False,
    )
    supplier_rank = fields.Integer(
        default=0,
        copy=False,
    )
    customer_rank = fields.Integer(
        default=0,
        copy=False,
    )
    autopost_bills = fields.Selection(
        selection=[
            ("always", "Always"),
            ("ask", "Ask after 3 validations without edits"),
            ("never", "Never"),
        ],
        string="Auto-post bills",
        default="ask",
        required=True,
        help="Automatically post bills for this trusted partner",
    )

    property_outbound_payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        company_dependent=True,
        domain=lambda self: [
            ("journal_id.active", "=", True),
            ("payment_type", "=", "outbound"),
            ("company_id", "parent_of", self.env.company.id),
        ],
        check_company=True,
    )

    property_inbound_payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        company_dependent=True,
        domain=lambda self: [
            ("journal_id.active", "=", True),
            ("payment_type", "=", "inbound"),
            ("company_id", "parent_of", self.env.company.id),
        ],
        check_company=True,
    )

    @api.depends("company_id", "country_code")
    def _compute_fiscal_country_codes(self):
        super()._compute_fiscal_country_codes()
        for record in self:
            if record.country_code:
                codes = set(filter(None, record.fiscal_country_codes.split(",")))
                record.fiscal_country_codes = ",".join(
                    sorted(codes | {record.country_code})
                )

    def _get_fiscal_country_companies(self):
        return self.company_id or super()._get_fiscal_country_companies()

    @api.depends("company_id")
    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_group_codes(self):
        for partner in self:
            allowed_companies = partner.company_id or self.env.companies
            partner.fiscal_country_group_codes = list(
                {
                    code
                    for company in allowed_companies
                    for code in company.account_config_id.account_fiscal_country_group_codes
                }
            )

    @property
    def _order(self):
        res = super()._order
        rank_field = SEARCH_MODE_RANK_FIELDS.get(
            self.env.context.get("res_partner_search_mode")
        )
        if not rank_field:
            return res
        order_by_field = f"{rank_field} DESC"
        return "%s, %s" % (order_by_field, res) if res else order_by_field

    @api.depends_context("company")
    @_debug.perf.timed
    def _compute_credit_debit(self):
        self.debit = self.credit = False
        _debug.logic(
            "credit_debit_scope",
            partners=self,
            skipped=not self.ids,
            reason="no_stored_ids" if not self.ids else None,
        )
        if not self.ids:
            return
        query = self.env["account.move.line"]._search(
            [
                ("parent_state", "=", "posted"),
                ("company_id", "child_of", self.env.company.root_id.id),
            ],
            bypass_access=True,
        )
        self.env["account.move.line"].flush_model(
            [
                "account_id",
                "amount_residual",
                "company_id",
                "parent_state",
                "partner_id",
                "reconciled",
            ]
        )
        self.env["account.account"].flush_model(["account_type"])
        sql = SQL(
            """
            SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual)
            FROM %s
            LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
            WHERE a.account_type IN ('asset_receivable','liability_payable')
            AND account_move_line.partner_id = ANY(%s)
            AND account_move_line.reconciled IS NOT TRUE
            AND %s
            GROUP BY account_move_line.partner_id, a.account_type
            """,
            query.from_clause,
            list(self.ids),
            query.where_clause or SQL("TRUE"),
        )
        for pid, account_type, val in self.env.execute_query(sql):
            partner = self.browse(pid)
            if account_type == "asset_receivable":
                partner.credit = val
            elif account_type == "liability_payable":
                partner.debit = -val

    @api.depends_context("company")
    def _compute_credit_to_invoice(self):
        self.credit_to_invoice = False

    def _get_asset_difference_query(self, account_type, operator, operand):
        return SQL(
            """
            SELECT aml.partner_id
              FROM account_move_line aml
              JOIN account_move move ON move.id = aml.move_id
              JOIN account_account acc ON acc.id = aml.account_id
              JOIN res_company line_company ON line_company.id = aml.company_id
             WHERE acc.account_type = %(account_type)s
               AND aml.partner_id IS NOT NULL
               AND SPLIT_PART(line_company.parent_path, '/', 1)::int = %(root_id)s
               AND move.state = 'posted'
          GROUP BY aml.partner_id
            HAVING %(sign)s * COALESCE(SUM(aml.amount_residual), 0)
                   %(operator)s %(operand)s
            """,
            account_type=account_type,
            root_id=self.env.company.root_id.id,
            sign=-1 if account_type == "liability_payable" else 1,
            operator=SQL(operator),  # noqa: E8501  caller whitelists the operator
            operand=operand,
        )

    def _asset_difference_search(self, account_type, operator, operand):
        if operator not in ASSET_DIFFERENCE_COMPARISONS:
            return NotImplemented
        if operand is False:
            operand = 0.0
        elif isinstance(operand, bool) or not isinstance(operand, (float, int)):
            return NotImplemented

        if ASSET_DIFFERENCE_COMPARISONS[operator](0.0, operand):
            negated = ASSET_DIFFERENCE_NEGATIONS[operator]
            _debug.logic(
                "asset_difference_negated",
                account_type=account_type,
                operator=operator,
                negated=negated,
                operand=operand,
            )
            return Domain(
                "id",
                "not any!",
                self._get_asset_difference_query(account_type, negated, operand),
            )
        return Domain(
            "id",
            "any!",
            self._get_asset_difference_query(account_type, operator, operand),
        )

    @api.model
    @_debug.perf.timed
    def _search_credit(self, operator, operand):
        return self._asset_difference_search("asset_receivable", operator, operand)

    @api.model
    @_debug.perf.timed
    def _search_debit(self, operator, operand):
        return self._asset_difference_search("liability_payable", operator, operand)

    @api.depends_context("allowed_company_ids")
    def _compute_total_invoiced(self):
        totals = self._aggregate_by_partner_hierarchy(
            "account.invoice.report",
            [
                ("state", "not in", ["draft", "cancel"]),
                ("move_type", "in", ("out_invoice", "out_refund")),
            ],
            "price_subtotal:sum",
        )
        for partner in self:
            partner.total_invoiced = totals[partner.id]

    @api.depends_context("company", "tz")
    @api.depends("credit")
    @_debug.perf.timed
    def _compute_days_sales_outstanding(self):
        commercial_partners = {
            commercial_partner: (invoice_date_min, amount_total_signed_sum)
            for commercial_partner, invoice_date_min, amount_total_signed_sum in self.env[
                "account.move"
            ]._read_group(
                domain=[
                    ("state", "not in", ["draft", "cancel"]),
                    (
                        "move_type",
                        "in",
                        self.env["account.move"].get_sale_types(include_receipts=True),
                    ),
                    ("company_id", "child_of", self.env.company.root_id.id),
                    ("commercial_partner_id", "in", self.commercial_partner_id.ids),
                ],
                groupby=["commercial_partner_id"],
                aggregates=["invoice_date:min", "amount_total_signed:sum"],
            )
        }
        today = fields.Date.context_today(self)
        _debug.pipeline(
            "dso_invoice_groups_read",
            partners=self,
            commercial_groups=len(commercial_partners),
            today=today,
        )
        for partner in self:
            oldest_invoice_date, total_invoiced_tax_included = commercial_partners.get(
                partner.commercial_partner_id, (today, 0)
            )
            days_since_oldest_invoice = (today - oldest_invoice_date).days
            partner.days_sales_outstanding = (
                max(
                    0.0,
                    (partner.credit / total_invoiced_tax_included)
                    * days_since_oldest_invoice,
                )
                if total_invoiced_tax_included > 0
                else 0
            )

    def _compute_available_invoice_template_pdf_report_ids(self):
        reports = self.env[
            "account.move"
        ]._get_available_invoice_template_pdf_report_ids()
        for partner in self:
            partner.available_invoice_template_pdf_report_ids = reports

    @api.depends_context("company")
    @api.depends("company_id")
    def _compute_currency_id(self):
        default_company = self.env.company
        currency_by_company = {}
        for partner in self:
            company = partner.company_id or default_company
            currency = currency_by_company.get(company.id)
            if currency is None:
                currency = company.sudo().currency_id
                currency_by_company[company.id] = currency
            partner.currency_id = currency

    def _aggregate_by_partner_hierarchy(self, comodel, domain, aggregate):
        self_ids = set(self._ids)
        # a partner is readable by users who may not read what hangs off it; a
        # statistic over records they cannot see is 0, not an AccessError
        if not self.env[comodel].has_access("read"):
            return dict.fromkeys(self_ids, 0)
        all_partners = self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )
        groups = self.env[comodel]._read_group(
            domain=[("partner_id", "in", all_partners.ids), *domain],
            groupby=["partner_id"],
            aggregates=[aggregate],
        )
        result = dict.fromkeys(self_ids, 0)
        for partner, value in groups:
            while partner:
                if partner.id in self_ids:
                    result[partner.id] += value
                partner = partner.parent_id
        return result

    def _compute_move_count_by_partner(self, field, move_domain):
        counts = self._aggregate_by_partner_hierarchy(
            "account.move", move_domain, "__count"
        )
        for partner in self:
            partner[field] = counts[partner.id]

    @api.model
    def _get_domain_supplier_bill(self):
        return [
            *self.env["account.move"]._check_company_domain(self.env.company),
            ("move_type", "in", ("in_invoice", "in_refund")),
        ]

    @api.depends_context("company")
    def _compute_supplier_invoice_count(self):
        self._compute_move_count_by_partner(
            "supplier_invoice_count", self._get_domain_supplier_bill()
        )

    @api.depends_context("company")
    def _compute_customer_invoice_count(self):
        self._compute_move_count_by_partner(
            "customer_invoice_count",
            [
                *self.env["account.move"]._check_company_domain(self.env.company),
                ("move_type", "in", ("out_invoice", "out_refund")),
            ],
        )

    @api.depends_context("company")
    @api.depends("country_code", "commercial_partner_id")
    def _compute_invoice_edi_format(self):
        for partner in self:
            commercial_partner = partner.commercial_partner_id
            stored = commercial_partner.invoice_edi_format_store
            if not commercial_partner or stored == "none":
                partner.invoice_edi_format = False
            else:
                partner.invoice_edi_format = (
                    stored or commercial_partner._get_suggested_invoice_edi_format()
                )

    def _inverse_invoice_edi_format(self):
        for partner in self:
            commercial_partner = partner.commercial_partner_id or partner
            edi_format = partner.invoice_edi_format
            if edi_format == commercial_partner._get_suggested_invoice_edi_format():
                stored = False
            elif not edi_format:
                stored = "none"
            else:
                stored = edi_format
            commercial_partner.invoice_edi_format_store = stored

    @api.depends("credit_limit")
    @api.depends_context("company")
    def _compute_use_partner_credit_limit(self):
        company_limit = self._fields["credit_limit"].get_company_dependent_fallback(
            self
        )
        for partner in self:
            partner.use_partner_credit_limit = partner.credit_limit != company_limit

    def _inverse_use_partner_credit_limit(self):
        company_limit = self._fields["credit_limit"].get_company_dependent_fallback(
            self
        )
        for partner in self:
            if not partner.use_partner_credit_limit:
                partner.credit_limit = company_limit

    @api.depends_context("company")
    def _compute_show_credit_limit(self):
        self.show_credit_limit = (
            self.env.company.account_config_id.account_use_credit_limit
        )

    @api.depends_context("uid")
    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        if not self.env.user.has_group("account.group_account_invoice"):
            return data_list
        for partner in self:
            count = partner._get_account_statistics_count()
            if not count:
                continue
            data_list[partner.id].append(
                {
                    "iconClass": "fa-solid fa-pen-to-square",
                    "value": count,
                    "label": _("Invoices/Bills/Mandates"),
                    "tagClass": "o_tag_color_9",
                }
            )
        return data_list

    def _get_account_statistics_count(self):
        return self.account_move_count + self.supplier_invoice_count

    def _get_suggested_invoice_edi_format(self):
        self.check_singleton()
        return False

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "property_account_payable_id",
            "property_account_receivable_id",
            "property_account_position_id",
            "property_payment_term_id",
            "property_supplier_payment_term_id",
            "credit_limit",
        ]

    @_debug.perf.timed
    def action_view_partner_invoices(self):
        _debug.lifecycle("action_view_partner_invoices", records=self)
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_move_out_invoice_type"
        )
        all_child = self.with_context(active_test=False).search(
            [("id", "child_of", self.ids)]
        )
        action["domain"] = [
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("partner_id", "in", all_child.ids),
        ]
        action["context"] = {
            "default_move_type": "out_invoice",
            "move_type": "out_invoice",
            "journal_type": "sale",
            "search_default_unpaid": 1,
        }
        return action

    @_debug.perf.timed
    def action_view_partner_bills(self):
        _debug.lifecycle("action_view_partner_bills", records=self)
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.res_partner_action_supplier_bills"
        )
        all_child = self.with_context(active_test=False).search(
            [("id", "child_of", self.ids)]
        )
        action["domain"] = [
            *self._get_domain_supplier_bill(),
            ("partner_id", "in", all_child.ids),
        ]
        action["context"] = {
            "default_move_type": "in_invoice",
            "default_partner_id": self.id,
        }
        return action

    def _has_invoice(self, partner_domain):
        self.check_singleton()
        return bool(
            self.env["account.move"]
            .sudo()
            .search_count(
                Domain.AND(
                    [
                        partner_domain,
                        [
                            ("move_type", "in", ["out_invoice", "out_refund"]),
                            ("state", "=", "posted"),
                        ],
                    ]
                ),
                limit=1,
            )
        )

    def _can_edit_country(self):
        return super()._can_edit_country() and not self._has_invoice(
            [("partner_id", "=", self.id)]
        )

    def can_edit_vat(self):
        return super().can_edit_vat() and not self._has_invoice(
            [("partner_id", "child_of", self.commercial_partner_id.id)]
        )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        partner2move_lines = {}
        if "parent_id" in vals:
            parent_write = self.filtered(
                lambda partner: partner.parent_id.id != vals["parent_id"]
            )
            if parent_write:
                partner2move_lines = (
                    self.env["account.move.line"]
                    .sudo()
                    .search([("partner_id", "in", parent_write.ids)])
                    .grouped("partner_id")
                )
                _debug.logic(
                    "parent_change_move_lines",
                    partners=parent_write,
                    with_lines=len(partner2move_lines),
                )
                self._check_parent_vat_matches(vals["parent_id"], partner2move_lines)

        res = super().write(vals)

        if partner2move_lines:
            self._update_accounting_commercial_partner(partner2move_lines)
        return res

    @_debug.perf.timed
    def _check_parent_vat_matches(self, parent_id, partner2move_lines):
        if not parent_id:
            return
        parent_id = self._fields["parent_id"].convert_to_cache(parent_id, self)
        parent_vat = self.browse(parent_id).vat or ""
        mismatched = next(
            (
                partner
                for partner in partner2move_lines
                if (partner.vat or "") != parent_vat
            ),
            None,
        )
        if mismatched is not None:
            _debug.logic("parent_vat_mismatch", partner=mismatched, parent=parent_id)
            raise UserError(
                _(
                    "You cannot set a partner as an invoicing address of another if they have a different %(vat_label)s.",
                    vat_label=mismatched.vat_label,
                )
            )

    def _update_accounting_commercial_partner(self, partner2move_lines):
        AccountMoveLine = self.env["account.move.line"].sudo()
        AccountMove = self.env["account.move"].sudo()
        lines_by_commercial = defaultdict(lambda: AccountMoveLine)
        moves_by_commercial = defaultdict(lambda: AccountMove)
        for partner, move_lines in partner2move_lines.items():
            commercial_partner = partner.commercial_partner_id
            lines_by_commercial[commercial_partner] |= move_lines
            moves_by_commercial[commercial_partner] |= move_lines.move_id.filtered(
                lambda move, partner=partner: move.partner_id == partner
            )

        unlocked = {"bypass_lock_check": BYPASS_LOCK_CHECK}
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "_update_accounting_commercial_partner",
                lines_moves_by_partner={
                    cp.id: (len(lines), len(moves_by_commercial[cp]))
                    for cp, lines in lines_by_commercial.items()
                },
            )
        for commercial_partner, move_lines in lines_by_commercial.items():
            move_lines.with_context(**unlocked).partner_id = commercial_partner
        for commercial_partner, moves in moves_by_commercial.items():
            if moves:
                moves.with_context(
                    **unlocked
                ).commercial_partner_id = commercial_partner

        body = _(
            "The commercial partner has been updated for all related accounting entries."
        )
        updated = self.browse(partner.id for partner in partner2move_lines).sudo()
        updated._message_log_batch(bodies=dict.fromkeys(updated.ids, body))

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
        rank_field = SEARCH_MODE_RANK_FIELDS.get(
            self.env.context.get("res_partner_search_mode")
        )
        if rank_field:
            vals_list = [{rank_field: 1, **vals} for vals in vals_list]
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_if_partner_in_account_move(self):
        _debug.lifecycle("_unlink_if_partner_in_account_move", records=self)
        moves = (
            self.env["account.move"]
            .sudo()
            .search_count(
                [
                    ("partner_id", "in", self.ids),
                    ("state", "in", ["draft", "posted"]),
                ],
                limit=1,
            )
        )
        if moves:
            raise UserError(
                _("The partner cannot be deleted because it is used in Accounting")
            )

    @_debug.perf.timed
    def _increase_rank(self, field: str, n: int = 1):
        assert field in ("customer_rank", "supplier_rank")
        if not self:
            return
        postcommit = self.env.cr.postcommit
        data = postcommit.data.setdefault(
            f"account.res.partner.increase_rank.{field}", defaultdict(int)
        )
        already_registered = bool(data)
        for record in self.sudo():
            if record[field] and record.id:
                data[record.id] += n
            else:
                record[field] += n

        _debug.logic(
            "rank_increase_routed",
            partners=self,
            field=field,
            n=n,
            deferred=len(data),
            already_registered=already_registered,
            register_hook=not (already_registered or not data),
        )
        if already_registered or not data:
            return

        _debug.lifecycle(
            "_increase_rank_registered_postcommit", field=field, data_count=len(data)
        )

        @postcommit.add
        def increase_partner_rank():
            try:
                with self.env.registry.cursor() as cr:
                    cr.execute(
                        SQL(
                            """
                            UPDATE res_partner partner
                               SET %(column)s = partner.%(column)s + increments.value
                              FROM (SELECT * FROM unnest(%(ids)s, %(values)s))
                                   AS increments(id, value)
                             WHERE partner.id = increments.id
                            """,
                            column=SQL.identifier(field),
                            ids=list(data),
                            values=list(data.values()),
                        )
                    )
                    _debug.pipeline(
                        "rank_increments_flushed",
                        field=field,
                        partners=len(data),
                        rows=cr.rowcount,
                    )
                data.clear()
            except Exception:
                _logger.warning(
                    "Cannot update %s for %s partner(s); the increments are lost.",
                    field,
                    len(data),
                    exc_info=True,
                )

    def _get_fields_frontend_writable(self):
        frontend_writable_fields = super()._get_fields_frontend_writable()
        frontend_writable_fields.update(
            {"invoice_sending_method", "invoice_edi_format"}
        )

        return frontend_writable_fields

    @_debug.perf.timed
    def _check_vat(self, validation="error"):
        for partner in self:
            vat, _country_code = self._run_vat_checks(
                partner.commercial_partner_id.country_id,
                partner.vat,
                partner_name=partner.name,
                validation=validation,
            )
            if vat != partner.vat:
                partner.vat = vat

    @api.model
    @_debug.perf.timed
    def _run_vat_checks(self, country, vat, partner_name="", validation="error"):
        assert validation in (False, "error", "setnull")
        return vat, (country and country.code) or ""

    def _is_vat_required_valid(self, company=None):
        self.check_singleton()
        return bool(self.vat)

    @api.model
    def get_partner_localisation_fields_required_to_invoice(self, country_id):
        return []

    @api.model
    @_debug.perf.timed
    def _get_import_criteria_from_vat(self, customer_values):
        vat = customer_values.get("vat")
        if not vat:
            return None

        normalized_vat = vat.replace(" ", "").replace(".", "")
        prefix_match = re.match(r"[a-zA-Z]{2}", vat)
        country_prefix = prefix_match.group() if prefix_match else ""

        criteria = [{"domain": [("vat", "in", (normalized_vat, vat))]}]
        extra_vat_values = self._get_country_specific_vat_variants(
            normalized_vat, country_prefix
        )
        if extra_vat_values:
            criteria.append({"domain": [("vat", "in", extra_vat_values)]})
        if country_prefix:
            criteria.append(
                {
                    "domain": [
                        ("vat", "in", (normalized_vat[2:], vat[2:])),
                        ("country_id.code", "=", country_prefix.upper()),
                    ],
                }
            )
            criteria.append(
                {
                    "domain": [
                        ("vat", "in", (normalized_vat[2:], vat[2:])),
                        ("country_id.code", "=", False),
                    ],
                }
            )

        try:
            vat_only_numeric = str(int(re.sub(r"^\D{2}", "", normalized_vat) or 0))
        except ValueError:
            vat_only_numeric = None
        if vat_only_numeric:

            def search_vat_regex(values):
                static_domain = values["static_domain"]
                vat_prefix_regex = values["vat_prefix_regex"]

                query = self._search(
                    Domain.AND([static_domain, [("active", "=", True)]]), limit=2
                )
                query.add_where(
                    SQL(
                        "%s ~ %s",
                        self._field_to_sql(self._table, "vat"),
                        f"^{vat_prefix_regex}0*{vat_only_numeric}$",
                    )
                )
                partner_row = list(query)
                if partner_row and len(partner_row) == 1:
                    return self.browse(partner_row[0])
                return self.browse()

            if country_prefix:
                vat_prefix_regex = f"({country_prefix})?"
            else:
                vat_prefix_regex = "([A-Za-z]{2})?"

            criteria.append(
                {
                    "vat_prefix_regex": vat_prefix_regex,
                    "search_method": search_vat_regex,
                }
            )

        _debug.pipeline(
            "vat_criteria_built",
            criteria=len(criteria),
            country_prefix=country_prefix,
            country_variants=bool(extra_vat_values),
            numeric_regex=bool(vat_only_numeric),
        )
        return {
            "criteria": criteria,
        }

    @api.model
    def _get_country_specific_vat_variants(self, normalized_vat, country_prefix):
        return []

    @api.model
    def _get_import_criteria_from_bank_account_number(self, customer_values):
        account_numbers = customer_values.get("account_numbers")
        if not account_numbers:
            return None

        return {
            "criteria": [
                {
                    "domain": [
                        (
                            "bank_ids",
                            "any",
                            [
                                "&",
                                ("acc_number", "in", account_numbers),
                                ("allow_out_payment", "=", True),
                            ],
                        ),
                    ],
                }
            ]
        }

    @api.model
    def _get_import_criteria_from_phone(self, customer_values):
        phone = customer_values.get("phone")
        if not phone:
            return None

        return {
            "criteria": [
                {
                    "domain": [
                        (
                            "phone_ids.sanitized",
                            "=",
                            self.env["phone.number"]._normalize_number(phone),
                        )
                    ],
                }
            ],
        }

    @api.model
    def _get_import_criteria_from_email(self, customer_values):
        email = customer_values.get("email")
        if not email:
            return None

        return {
            "criteria": [
                {
                    "domain": [("email", "=", email)],
                }
            ],
        }

    @api.model
    def _get_import_criteria_from_name(self, customer_values):
        name = customer_values.get("name")
        if not name:
            return None

        return {
            "criteria": [
                {
                    "domain": [("name", "=ilike", name)],
                }
            ],
        }

    def _get_first_partner(self, domain):
        return self.search(
            domain,
            order="is_company DESC, supplier_rank DESC, company_id, parent_id DESC, id DESC",
            limit=1,
        )

    @api.model
    @_debug.perf.timed
    def _update_customer_values_from_search_plan(
        self, search_plan, company, customer_values_list
    ):
        cache = {}

        static_domain = Domain.OR(
            [
                [*self._check_company_domain(company), ("company_id", "!=", False)],
                [("company_id", "=", False)],
            ]
        )
        _debug.pipeline(
            "customer_search_started",
            company=company,
            plans=len(search_plan),
            customers=len(customer_values_list),
        )
        for customer_values in customer_values_list:
            partner = None
            for plan in search_plan:
                plan_values = plan(customer_values)
                if not plan_values:
                    continue

                for criteria in plan_values["criteria"]:
                    domain = criteria.get("domain")
                    search_method = criteria.get("search_method")
                    cache_key = str(domain) if domain else criteria.get("cache_key")

                    if cache_key is not None and cache_key in cache:
                        partner = cache[cache_key]
                    elif domain:
                        partner = self._get_first_partner(
                            Domain.AND([static_domain, domain])
                        )
                    elif search_method:
                        partner = search_method(
                            {
                                **criteria,
                                "static_domain": static_domain,
                            }
                        )
                    else:
                        continue

                    if cache_key is not None:
                        cache[cache_key] = partner
                    if partner:
                        customer_values["customer"] = partner
                        break

                if partner:
                    break
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "customer_search_done",
                company=company,
                customers=len(customer_values_list),
                matched=sum(
                    1 for values in customer_values_list if values.get("customer")
                ),
                cache_keys=len(cache),
            )

    def _get_import_customer_search_plan(self, domain=None):
        return [
            (5, self._get_import_criteria_from_vat),
            (
                10,
                lambda customer_values: (
                    {"criteria": [{"domain": domain}]} if domain else None
                ),
            ),
            (15, self._get_import_criteria_from_bank_account_number),
            (20, self._get_import_criteria_from_email),
            (25, self._get_import_criteria_from_phone),
            (30, self._get_import_criteria_from_name),
        ]

    def _get_matching_partner(
        self,
        name=None,
        phone=None,
        email=None,
        vat=None,
        domain=None,
        company=None,
        account_numbers=None,
    ):
        customer_values = {
            "vat": vat,
            "phone": phone,
            "email": email,
            "name": name,
            "account_numbers": account_numbers,
        }
        self._update_customer_values_from_search_plan(
            search_plan=[
                method
                for _priority, method in sorted(
                    self._get_import_customer_search_plan(domain=domain),
                    key=lambda plan: plan[0],
                )
            ],
            company=company or self.env.company,
            customer_values_list=[customer_values],
        )
        partner = customer_values.get("customer") or self.browse()
        _debug.logic(
            "import_match",
            by_name=bool(name),
            by_vat=bool(vat),
            by_email=bool(email),
            partner=partner,
        )
        return partner

    def _merge_method(self, destination, source):
        if (
            self.env["account.move.line"]
            .sudo()
            .search_count(
                [
                    ("move_id.inalterable_hash", "!=", False),
                    ("partner_id", "in", source.ids),
                ],
                limit=1,
            )
        ):
            raise UserError(
                _("Partners that are used in hashed entries cannot be merged.")
            )
        return super()._merge_method(destination, source)

    def _deduce_country_code(self):
        self.check_singleton()
        _vat, country_code = self._run_vat_checks(
            self.country_id, self.vat, validation=False
        )
        return country_code or self.country_code

    @api.model
    def _get_expected_vat_format(self, country_code):
        return ""

    @api.depends("country_id")
    def _compute_partner_vat_placeholder(self):
        for partner in self:
            expected_vat = self._get_expected_vat_format(partner.country_id.code)
            partner.partner_vat_placeholder = (
                _("%s, or not applicable", expected_vat)
                if expected_vat
                else _("not applicable")
            )

    @api.depends("country_id.code", "ref_company_ids.account_config_id.account_fiscal_country_id.code")
    def _compute_company_registry_placeholder(self):
        super()._compute_company_registry_placeholder()
        for partner in self:
            country = (
                partner.ref_company_ids[:1].account_config_id.account_fiscal_country_id
                or partner.country_id
            )
            partner.company_registry_placeholder = _ref_company_registry.get(
                (country.code or "").lower(), ""
            )

    @api.depends_context("allowed_company_ids")
    def _compute_account_move_count(self):
        self._compute_move_count_by_partner(
            "account_move_count",
            [("move_type", "in", ("out_invoice", "out_refund"))],
        )

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        return self._get_records_action()

    @api.model
    def _clear_removed_edi_formats(self, *formats):
        self.flush_model(["invoice_edi_format_store"])
        self.env.cr.execute(
            SQL(
                """
                UPDATE res_partner
                   SET invoice_edi_format_store = invoice_edi_format_store - (
                       SELECT COALESCE(array_agg(entry.company_id), ARRAY[]::text[])
                         FROM jsonb_each_text(invoice_edi_format_store)
                              AS entry(company_id, format)
                        WHERE entry.format = ANY(%(formats)s))
                 WHERE jsonb_typeof(invoice_edi_format_store) = 'object'
                """,
                formats=list(formats),
            )
        )
        _debug.perf.count("edi_formats_cleared", rows=self.env.cr.rowcount)
        self.invalidate_model(["invoice_edi_format_store"])
