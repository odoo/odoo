from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, format_list

from odoo.addons.base.models.mixin_lifecycle import MixinLifecycle

_debug = DebugLog(__name__)


class MixinOrder(models.AbstractModel):
    _name = "mixin.order"
    _description = "Order Management Base"
    _inherit = [
        "mixin.lifecycle",
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.portal",
        "mixin.product.catalog",
    ]

    _order_type = ""

    _sequence_code = ""
    _invoice_move_direction = ""
    _partner_payment_term_field = ""
    _lock_setting_field = ""
    _auto_lock_group = ""
    _mark_sent_context_key = ""
    _display_name_context_key = ""
    _portal_url_prefix = ""
    _product_ok_field = ""

    _price_history_action = ""

    _STATE_TRANSITIONS = {
        "draft": {"done", "cancel"},
        "done": {"cancel"},
        "cancel": {"draft"},
    }
    _LOCKED_WRITABLE_FIELDS = {
        *MixinLifecycle._LOCKED_WRITABLE_FIELDS,
        "priority",
        "access_token",
        "acknowledged",
        "sent",
        "count_sent",
        "printed_before",
        "count_print",
    }

    @property
    def _rec_names_search(self):
        base_fields = self._get_fields_rec_search_base()
        if self.env.context.get(self._get_display_name_context_key()):
            return [*base_fields, "partner_id.name"]
        return base_fields

    def _get_fields_rec_search_base(self):
        return ["name"]

    def _get_display_name_context_key(self):
        return self._display_name_context_key

    line_ids = fields.One2many(
        comodel_name="mixin.order.line.fields",
        inverse_name="order_id",
        string="Order Lines",
        copy=True,
    )

    show_comparison = fields.Boolean(
        compute="_compute_show_comparison",
        help="Whether any product on this order was also bought or sold on "
        "another confirmed order, so a price comparison has something to show.",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
    )

    name = fields.Char(
        string="Order Reference",
        default=lambda self: _("New"),
        index="trigram",
        copy=False,
        readonly=False,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Confirmed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
    )
    priority = fields.Selection(
        selection=[
            ("0", "Normal"),
            ("1", "Urgent"),
        ],
        default="0",
        index=True,
    )

    date_order = fields.Datetime(
        string="Order Date",
        default=fields.Datetime.now,
        index=True,
        copy=False,
        required=True,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        index=True,
        copy=False,
        readonly=True,
        help="Date when the order was confirmed.",
    )
    date_commitment = fields.Datetime(
        string="Commitment Date",
        copy=False,
        help="The date somebody committed to: the delivery date promised to "
        "the customer on a sale, the arrival date promised by the vendor on a "
        "purchase.",
    )
    date_validity = fields.Date(
        string="Expiration",
        compute="_compute_date_validity",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Validity of the quotation, after which it expires.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    company_price_include = fields.Selection(related="company_id.account_price_include")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        ondelete="restrict",
    )
    currency_rate = fields.Float(
        digits=0,
        compute="_compute_currency_rate",
        precompute=True,
        store=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        change_default=True,
        index=True,
        required=True,
        domain=lambda self: self._domain_partner_id(),
        check_company=True,
        tracking=True,
    )
    commercial_partner_id = fields.Many2one(
        related="partner_id.commercial_partner_id",
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        compute="_compute_user_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        domain="[('share', '=', False), ('company_ids', '=', company_id)]",
        tracking=True,
    )

    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        compute="_compute_payment_term_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
        check_company=True,
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        compute="_compute_fiscal_position_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
        check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular "
        "partners or orders/invoices. The default value comes from the partner.",
    )
    tax_country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_tax_country_id",
        # The fiscal position may belong to a company the reading user cannot access.
        compute_sudo=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        precompute=True,
        store=True,
        readonly=False,
        check_company=True,
        help="If set, the order will invoice in this journal; otherwise the "
        "journal with the lowest sequence is used.",
    )

    locked = fields.Boolean(tracking=True)
    acknowledged = fields.Boolean(
        copy=False,
        tracking=True,
        help="It indicates that the partner has acknowledged the receipt of the order.",
    )

    sent = fields.Boolean(
        default=False,
        copy=False,
        tracking=True,
        help="The order has been sent to the partner.",
    )
    count_sent = fields.Integer(
        string="Sent Count",
        default=0,
        copy=False,
    )
    printed_before = fields.Boolean(
        default=False,
        copy=False,
        tracking=True,
        help="The order has already been printed.",
    )
    count_print = fields.Integer(
        string="Print Count",
        default=0,
        copy=False,
    )

    origin = fields.Char(
        string="Source Document",
        copy=False,
        help="Reference of the document that generated this order request.",
    )
    partner_ref = fields.Char(
        string="Partner Reference",
        copy=False,
    )

    notes = fields.Html(string="Terms and Conditions")

    duplicated_order_ids = fields.Many2many(
        comodel_name="mixin.order",
        compute="_compute_duplicated_order_ids",
    )

    is_expired = fields.Boolean(compute="_compute_is_expired")
    is_late = fields.Boolean(
        compute="_compute_is_late",
        search="_search_is_late",
        help="True when the order is confirmed and its planned date has passed.",
    )
    type_name = fields.Char(compute="_compute_type_name")
    has_archived_products = fields.Boolean(compute="_compute_has_archived_products")

    @api.depends("company_id", "line_ids", "line_ids.product_id")
    def _compute_show_comparison(self):
        Line = self.env[self.line_ids._name]
        order_by_product_by_company = {}
        for company in self.company_id:
            order_by_product_by_company[company] = {
                product: set(order_ids)
                for product, order_ids in Line._read_group(  # noqa: E8507 - one query per company; orders sharing one were merged above
                    [
                        ("product_id", "in", self.line_ids.product_id.ids),
                        ("state", "=", "done"),
                        ("company_id", "in", company._get_accessible_branches().ids),
                    ],
                    ["product_id"],
                    ["order_id:array_agg"],
                )
            }
        _debug.perf.count(
            "show_comparison",
            orders=len(self),
            companies=len(order_by_product_by_company),
        )
        for order in self:
            order_by_product = order_by_product_by_company.get(order.company_id, {})
            order.show_comparison = any(
                set(order.ids) != order_by_product[p]
                for p in order.line_ids.product_id
                if p in order_by_product
            )

    def action_price_comparison(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            self._price_history_action,
        )
        action["display_name"] = _("Price Comparison for %s", self.display_name)
        action["domain"] = [
            ("state", "=", "done"),
            ("product_id", "in", self.line_ids.product_id.ids),
            ("company_id", "in", self.company_id._get_accessible_branches().ids),
        ]
        return action

    def _get_order_type(self):
        if not self._order_type:
            _debug.logic("order_type_undeclared", model=self._name)
            raise NotImplementedError(f"{self._name} must declare _order_type")
        return self._order_type

    def _domain_partner_id(self):
        if self._abstract:
            return []
        return self.env["res.partner.tag"]._get_domain_partner_allowed(
            self._get_order_type(),
        )

    def _get_line_model(self):
        return f"{self._name}.line"

    @api.model_create_multi
    def create(self, vals_list):
        seq_code = self._sequence_code
        default_company_id = None
        # the orders of one company and one date draw their names from the
        # sequence in one batch, in the order they are created
        unnamed_by_key = defaultdict(list)
        for vals in vals_list:
            if "company_id" in vals:
                company_id = vals["company_id"]
            else:
                if default_company_id is None:
                    default_company_id = self.default_get(["company_id"])["company_id"]
                company_id = default_company_id
            self_comp = self.with_company(company_id)
            if vals.get("name", _("New")) == _("New"):
                if "date_order" in vals:
                    date_order = vals["date_order"]
                else:
                    date_order = self_comp.default_get(["date_order"])["date_order"]
                seq_date = fields.Datetime.context_timestamp(
                    self_comp,
                    fields.Datetime.to_datetime(date_order),
                )
                unnamed_by_key[(company_id, seq_date)].append(vals)
        for (company_id, seq_date), unnamed in unnamed_by_key.items():
            names = (
                self.with_company(company_id)
                .env["ir.sequence"]
                .next_by_code_batch(seq_code, len(unnamed), sequence_date=seq_date)
            )
            for vals, name in zip(
                unnamed, names or [False] * len(unnamed), strict=True
            ):
                vals["name"] = name
        _debug.pipeline(
            "order_names_from_sequence",
            model=self._name,
            rows=len(vals_list),
            batches=len(unnamed_by_key),
        )
        _debug.lifecycle("create", model=self._name, rows=len(vals_list))
        return super().create(vals_list)

    def write(self, vals):
        _debug.lifecycle("write", orders=self, fields=list(vals))
        return super().write(vals)

    def copy_data(self, default=None):
        default = dict(default or {})
        default_has_no_order_line = "line_ids" not in default
        default.setdefault("line_ids", [])
        vals_list = super().copy_data(default=default)
        if default_has_no_order_line:
            for order, vals in zip(self, vals_list, strict=False):
                vals["line_ids"] = [
                    Command.create(line_vals)
                    for line_vals in order._get_order_lines_copiable().copy_data()
                ]
                _debug.pipeline(
                    "order_lines_copied",
                    order=order,
                    lines=len(vals["line_ids"]),
                )
        return vals_list

    def _get_order_lines_copiable(self):
        return self.line_ids.filtered(lambda line: not line.is_downpayment)

    @api.constrains("company_id", "line_ids")
    def _check_line_ids_company_id(self):
        for order in self:
            invalid_companies = order.line_ids.product_id.company_id.filtered(
                lambda c, order=order: (
                    order.company_id not in c._get_accessible_branches()
                ),
            )
            if invalid_companies:
                bad_products = order.line_ids.product_id.filtered(
                    lambda p, invalid=invalid_companies: (
                        p.company_id and p.company_id in invalid
                    ),
                )
                _debug.logic(
                    "company_consistency_refused",
                    order=order,
                    products=bad_products,
                    companies=invalid_companies,
                )
                raise ValidationError(
                    _(
                        "Your %(desc)s contains products from company %(product_company)s "
                        "whereas your %(desc)s belongs to company %(quote_company)s.\n\n"
                        "Please change the company of your %(desc)s or remove the products "
                        "from other companies (%(bad_products)s).",
                        desc=self._description.lower(),
                        product_company=", ".join(
                            invalid_companies.sudo().mapped("display_name"),
                        ),
                        quote_company=order.company_id.display_name,
                        bad_products=", ".join(bad_products.mapped("display_name")),
                    ),
                )

    @api.depends("company_id", "currency_id", "date_order")
    def _compute_currency_rate(self):
        _debug.perf.count("currency_rate", orders=len(self))
        for order in self:
            order.currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(order.date_order or fields.Datetime.now()).date(),
            )

    @api.depends("line_ids.product_id")
    def _compute_has_archived_products(self):
        for order in self:
            order.has_archived_products = any(
                not product.active for product in order.line_ids.product_id
            )

    def _compute_display_name(self):
        for order in self:
            order.display_name = f"{order.name}{order._get_display_name_suffix()}"

    def _get_display_name_suffix(self):
        return ""

    @api.depends("state", "date_validity")
    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = (
                order.state == "draft"
                and order.date_validity
                and order.date_validity < today
            )

    @api.depends("company_id")
    def _compute_date_validity(self):
        today = fields.Date.context_today(self)
        for order in self:
            days = order._get_validity_days()
            if days > 0:
                order.date_validity = today + timedelta(days=days)
            else:
                order.date_validity = False

    def _compute_journal_id(self):
        self.journal_id = False

    @api.depends_context("lang")
    @api.depends("state")
    def _compute_type_name(self):
        for order in self:
            if order.state in ("draft", "cancel"):
                order.type_name = order._get_draft_type_name()
            else:
                order.type_name = order._get_confirmed_type_name()

    @api.depends("state", "partner_id", "origin")
    def _compute_duplicated_order_ids(self):
        draft_orders = self.filtered(lambda order: order.state == "draft")
        order_to_duplicate_orders = draft_orders._get_duplicate_orders()
        _debug.perf.count(
            "duplicated_orders",
            orders=len(self),
            draft=len(draft_orders),
            with_duplicates=len(order_to_duplicate_orders),
        )
        for order in draft_orders:
            duplicate_ids = order_to_duplicate_orders.get(order.id, [])
            order.duplicated_order_ids = [Command.set(duplicate_ids)]
        (self - draft_orders).duplicated_order_ids = False

    @api.depends("company_id", "partner_id")
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = order.company_id.currency_id

    @api.depends("partner_id")
    def _compute_user_id(self):
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                order.user_id = order._get_default_user_from_partner()

    @api.depends("company_id", "partner_id")
    def _compute_payment_term_id(self):
        field_name = self._get_partner_payment_term_field()
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = order.partner_id[field_name]

    @api.depends("company_id", "partner_id")
    def _compute_fiscal_position_id(self):
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue

            key = (order.company_id.id, order.partner_id.id)
            if key not in cache:
                cache[key] = (
                    self.env["account.fiscal.position"]
                    .with_company(order.company_id)
                    ._get_fiscal_position(order.partner_id)
                    .id
                )
            order.fiscal_position_id = cache[key]

    @api.depends(
        "company_id.account_fiscal_country_id",
        "fiscal_position_id.country_id",
        "fiscal_position_id.foreign_vat",
    )
    def _compute_tax_country_id(self):
        for order in self:
            order.tax_country_id = order.fiscal_position_id._get_tax_country(
                order.company_id
            )

    @api.depends("state", "date_commitment")
    def _compute_is_late(self):
        self.is_late = False
        saved = self.filtered("id")._origin
        if not saved:
            return
        late = saved.search(
            Domain("id", "in", saved.ids) & Domain(self._search_is_late("=", True)),
        )
        for order in self:
            order.is_late = order._origin in late

    def _search_is_late(self, operator, value):
        if operator not in ("=", "!="):
            return NotImplemented
        domain = self._get_domain_is_late(operator, value)
        positive = (operator == "=" and value) or (operator == "!=" and not value)
        return self._get_domain_is_late_with_polarity(domain, positive)

    def _get_domain_is_late(self, operator, value):
        return Domain(
            [
                ("state", "=", "done"),
                ("date_commitment", "!=", False),
                ("date_commitment", "<=", fields.Datetime.now()),
            ]
        )

    def _get_domain_is_late_with_polarity(self, domain, positive):
        return domain if positive else ~domain

    def _get_draft_type_name(self):
        return _("Quotation")

    def _get_confirmed_type_name(self):
        order_type = self._get_order_type()
        return _("%(type)s Order", type=order_type.title())

    def _get_validity_days(self):
        self.check_singleton()
        return 0

    def _get_partner_payment_term_field(self):
        return self._partner_payment_term_field

    def _get_default_user_from_partner(self):
        self.check_singleton()
        return (
            self.env.user
            if self.env.user.has_group("base.group_user")
            else self.env["res.users"]
        )

    def _prepare_confirmation_values(self):
        return {"state": "done"}

    def _action_cancel(self):
        draft_invoices = self.invoice_ids.filtered(
            lambda invoice: invoice.state == "draft",
        )
        if draft_invoices:
            _debug.lifecycle("draft_invoices_cancelled", invoices=draft_invoices)
            draft_invoices.action_cancel()
        return super()._action_cancel()

    def _get_lock_setting_field(self):
        return self._lock_setting_field

    def _get_lock_setting_user(self):
        self.check_singleton()
        return self.env.user

    def _is_lock_required(self):
        self.check_singleton()
        if self.company_id[self._get_lock_setting_field()] == "lock":
            _debug.logic("lock_required", order=self, by="company_setting")
            return True
        group = self._auto_lock_group
        _debug.logic("lock_required_check", order=self, group=group or "none")
        return bool(group) and self._get_lock_setting_user().has_group(group)

    def _get_confirm_validation_methods(self):
        return [
            *super()._get_confirm_validation_methods(),
            "_check_confirm_has_lines",
            "_check_confirm_lines_have_product",
            "_check_confirm_analytic_distribution",
        ]

    def _requires_lines_to_confirm(self):
        self.check_singleton()
        return True

    def _check_confirm_has_lines(self):
        orders_without_lines = self.filtered(
            lambda order: not order.line_ids and order._requires_lines_to_confirm()
        )
        if orders_without_lines:
            _debug.logic(
                "confirm_refused", orders=orders_without_lines, reason="no_lines"
            )
            raise UserError(
                _(
                    "Cannot confirm %(desc)s without lines: %(orders)s\n\n"
                    "Please add at least one product line before confirming.",
                    desc=self._description,
                    orders=format_list(
                        self.env,
                        orders_without_lines.mapped("display_name"),
                    ),
                ),
            )

    def _check_confirm_lines_have_product(self):
        orders_without_line_product = self.filtered(
            lambda order: any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in order.line_ids
            ),
        )
        if not orders_without_line_product:
            return
        _debug.logic(
            "confirm_refused",
            orders=orders_without_line_product,
            reason="line_without_product",
        )
        error_details = []
        for order in orders_without_line_product:
            missing_product_lines = order.line_ids.filtered(
                lambda l: (
                    not l.display_type and not l.is_downpayment and not l.product_id
                ),
            )
            error_details.append(
                _(
                    "• %(order)s has %(count)d line(s) without products",
                    order=order.display_name,
                    count=len(missing_product_lines),
                ),
            )
        raise UserError(
            _(
                "Cannot confirm %(desc)s with lines missing products:\n\n%(details)s\n\n"
                "Please assign a product to all order lines before confirming.",
                desc=self._description,
                details="\n".join(error_details),
            ),
        )

    def _check_confirm_analytic_distribution(self):
        pass

    def action_acknowledge(self):
        _debug.lifecycle("order_acknowledged", orders=self)
        self.write({"acknowledged": True})

    def _mark_as_printed(self):
        for order in self:
            vals = {"count_print": order.count_print + 1}
            if order.state == "draft":
                vals["printed_before"] = True
            _debug.lifecycle("order_printed", order=order, count=vals["count_print"])
            order.write(vals)

    def action_view_business_doc(self):
        self.check_singleton()
        return {
            "name": _("Order"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
        }

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": self._get_import_template_label(),
                "template": self._get_import_template_path(),
            },
        ]

    def _get_import_template_label(self):
        raise NotImplementedError(
            f"{self._name} must implement _get_import_template_label()"
        )

    def _get_import_template_path(self):
        raise NotImplementedError(
            f"{self._name} must implement _get_import_template_path()"
        )

    def _get_check_write_guards(self):
        return [*super()._get_check_write_guards(), "_check_write_user_id"]

    def _check_write_user_id(self, vals):
        if "user_id" not in vals or self.env.su:
            return
        group = self._get_all_documents_group()
        if not group or self.env.user.has_group(group):
            return
        if vals["user_id"] == self.env.uid:
            return
        _debug.logic(
            "write_refused", orders=self, reason="reassign_without_all_documents_group"
        )
        raise AccessError(
            _(
                "You are limited to your own documents, so you may only make "
                "yourself responsible for an order. Ask someone with access to "
                "all documents to reassign it.",
            ),
        )

    def _get_all_documents_group(self):
        return False

    def _get_warning_group(self):
        return False

    def _get_partner_warn_field(self):
        return False

    def _get_line_warn_field(self):
        return False

    def _compute_warning_text(self, target_field):
        group = self._get_warning_group()
        if group and not self.env.user.has_group(group):
            setattr(self, target_field, "")
            _debug.logic(
                "warnings_skipped", orders=self, field=target_field, reason="no_group"
            )
            return

        partner_field = self._get_partner_warn_field()
        line_field = self._get_line_warn_field()
        for order in self:
            warnings = OrderedSet()
            if partner_field:
                partner = order.partner_id
                for record in (partner, partner.parent_id):
                    if msg := record[partner_field]:
                        warnings.add(
                            (record.name or record.display_name) + " - " + msg,
                        )
            if line_field:
                for line in order.line_ids:
                    if msg := line[line_field]:
                        warnings.add(line.product_id.display_name + " - " + msg)
            setattr(order, target_field, "\n".join(warnings))
            if _debug.logic.enabled and warnings:
                _debug.logic(
                    "order_warnings",
                    order=order,
                    field=target_field,
                    count=len(warnings),
                )

    def _get_duplicate_ref_field(self):
        return "partner_ref"

    def _get_duplicate_orders(self):
        ref_field = self._get_duplicate_ref_field()
        orders = self.filtered(
            lambda order: order.id and (order[ref_field] or order.origin),
        )
        if not orders:
            _debug.logic("duplicate_probe_skipped", orders=self, reason="no_reference")
            return {}

        self.flush_model(
            ["company_id", "partner_id", "name", ref_field, "origin", "state"],
        )

        _debug.perf.count("duplicate_orders_probe", orders=orders)
        result = self.env.execute_query(
            SQL(
                """
                SELECT o.id AS order_id,
                       array_agg(duplicate_order.id) AS duplicate_ids
                  FROM %(table)s o
                  JOIN %(table)s AS duplicate_order
                    ON o.company_id = duplicate_order.company_id
                   AND o.id != duplicate_order.id
                   AND duplicate_order.state != 'cancel'
                   AND o.partner_id = duplicate_order.partner_id
                   AND (
                        o.origin = duplicate_order.name
                        OR o.%(ref_field)s = duplicate_order.%(ref_field)s
                   )
                 WHERE o.id IN %(order_ids)s
                   AND o.state != 'cancel'
                 GROUP BY o.id
                """,
                table=SQL.identifier(self._table),
                ref_field=SQL.identifier(ref_field),
                order_ids=tuple(orders.ids),
            ),
        )
        return {order_id: set(duplicate_ids) for order_id, duplicate_ids in result}

    def _get_mark_sent_context_key(self):
        return self._mark_sent_context_key

    def _mark_as_sent(self):
        _debug.lifecycle("order_marked_sent", orders=self)
        for order in self:
            order.with_context(**order._prepare_mark_as_sent_context()).write(
                {"sent": True, "count_sent": order.count_sent + 1},
            )

    def _prepare_mark_as_sent_context(self):
        return {}

    def message_post(self, **kwargs):
        mark_key = self._get_mark_sent_context_key()
        if self.env.context.get(mark_key):
            self.filtered(lambda order: order.state == "draft")._mark_as_sent()
            kwargs["notify_author_mention"] = kwargs.get("notify_author_mention", True)
        return super().message_post(**kwargs)

    def _get_mail_compose_form(self):
        ir_model_data = self.env["ir.model.data"]
        try:
            compose_form_id = ir_model_data._get_xmlid_target(
                "mail.email_compose_message_wizard_form",
            )[1]
        except ValueError:
            compose_form_id = False
        return compose_form_id

    def _action_send_by_email(self):
        ctx = self._prepare_mail_composer_context()
        lang = self._get_mail_composer_lang(ctx)
        order = self.with_context(lang=lang) if lang else self
        ctx.update(order._prepare_mail_composer_lang_context())
        if lang:
            ctx["lang"] = lang
        compose_form_id = self._get_mail_compose_form()
        _debug.pipeline(
            "send_by_email_composer", orders=self, lang=lang or self.env.lang
        )
        return {
            "name": self._get_mail_composer_action_name(),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def _prepare_mail_composer_lang_context(self):
        return {}

    def _get_mail_composer_action_name(self):
        return _("Send")

    def _prepare_mail_composer_context(self):
        ctx = {
            "default_model": self._name,
            "default_res_ids": self.ids,
            "default_composition_mode": "comment",
            "default_email_layout_xmlid": (
                "mail.mail_notification_layout_with_responsible_signature"
            ),
            "email_notification_allow_footer": True,
            "hide_mail_template_management_options": True,
        }
        if len(self) > 1:
            ctx["default_composition_mode"] = "mass_mail"
        else:
            ctx.update(self._prepare_single_mail_composer_context())
        return ctx

    def _prepare_single_mail_composer_context(self):
        self.check_singleton()
        ctx = {"force_email": True}
        if self.env.context.get("hide_default_template"):
            self._portal_get_or_create_token()
            return ctx
        if mail_template := self._get_mail_template():
            ctx["default_template_id"] = mail_template.id
            ctx[self._get_mark_sent_context_key()] = True
            _debug.logic("composer_template", order=self, template=mail_template)
        return ctx

    def _get_mail_template(self):
        raise NotImplementedError(f"{self._name} must implement _get_mail_template()")

    def _get_mail_composer_lang(self, ctx):
        lang = self.env.context.get("lang")
        required = {"default_template_id", "default_model", "default_res_ids"}
        if not required <= ctx.keys():
            return lang
        res_ids = ctx["default_res_ids"]
        template = self.env["mail.template"].browse(ctx["default_template_id"])
        if res_ids and template.lang:
            lang = template._render_lang(res_ids)[res_ids[0]]
            _debug.logic("composer_lang", orders=self, by="template", lang=lang)
        return lang

    def _notify_by_email_prepare_rendering_context(
        self,
        message,
        msg_vals=False,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        force_record_name=False,
        tracking_values=None,
    ):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
            tracking_values=tracking_values,
        )
        render_context["subtitles"] = self._get_mail_subtitles(render_context)
        return render_context

    def _get_mail_subtitles(self, render_context):
        return []

    def _notify_get_recipients_groups(
        self,
        message,
        model_description,
        msg_vals=False,
    ):
        groups = super()._notify_get_recipients_groups(
            message,
            model_description,
            msg_vals=msg_vals,
        )
        if not self:
            return groups
        self.check_singleton()
        self._update_notify_recipient_groups(groups)
        return groups

    def _update_notify_recipient_groups(self, groups):
        return

    def _track_subtype(self, init_values):
        self.check_singleton()
        xmlid = self._get_state_track_subtype_xmlid(init_values)
        if xmlid:
            return self.env.ref(xmlid)
        return super()._track_subtype(init_values)

    def _get_state_track_subtype_xmlid(self, init_values):
        return

    def _get_portal_url_prefix(self):
        return self._portal_url_prefix

    def _compute_access_url(self):
        super()._compute_access_url()
        prefix = self._get_portal_url_prefix()
        for order in self:
            order.access_url = f"/my/{prefix}/{order.id}"

    def _get_report_base_filename(self):
        self.check_singleton()
        return f"{self.type_name} {self.name}"

    def _get_parent_field_on_child_model(self):
        return "order_id"

    def _get_order_line_values(self, child_field=False):
        default_data = super()._get_order_line_values(child_field)
        new_default_data = self.env[
            self._get_line_model()
        ]._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_product_catalog_record_lines(
        self,
        product_ids,
        *,
        section_id=None,
        **kwargs,
    ):
        grouped_lines = defaultdict(lambda: self.env[self._get_line_model()])
        if section_id is None:
            section_id = (
                self.line_ids[:1].id
                if self.line_ids[:1].display_type == "line_section"
                else False
            )
        for line in self.line_ids:
            if (
                line.display_type
                or line.product_id.id not in product_ids
                or line.get_line_parent_section().id != section_id
            ):
                continue
            grouped_lines[line.product_id] |= line
        _debug.perf.count(
            "catalog_record_lines",
            order=self,
            lines=len(self.line_ids),
            products=len(grouped_lines),
        )
        return grouped_lines

    def _prepare_catalog_extra_context(self):
        return {
            **super()._prepare_catalog_extra_context(),
            "product_catalog_currency_id": self.currency_id.id,
            "product_catalog_digits": self.line_ids._fields["price_unit"].get_digits(
                self.env,
            ),
            "show_sections": bool(self.id),
        }

    def _get_domain_product_catalog(self):
        return super()._get_domain_product_catalog() & Domain(
            self._get_catalog_product_ok_field(),
            "=",
            True,
        )

    def _get_catalog_product_ok_field(self):
        return self._product_ok_field

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        catalog_data = self._get_catalog_product_data(products, **kwargs)
        for product in products:
            res[product.id].update(catalog_data.get(product.id, {}))
        return res

    def _get_catalog_product_data(self, products, **kwargs):
        return {}

    def _update_order_line_info(
        self,
        product_id,
        quantity,
        *,
        section_id=False,
        child_field="line_ids",
        **kwargs,
    ):
        self.check_singleton()
        self._update_catalog_context()
        line = self.line_ids.filtered(
            lambda l: (
                l.product_id.id == product_id
                and l.get_line_parent_section().id == section_id
            ),
        )
        if line:
            if quantity != 0:
                line.product_qty = quantity
            elif self.state in self._get_catalog_editable_states():
                price_unit = self._get_catalog_removed_line_price(
                    line.product_id,
                    **kwargs,
                )
                line.unlink()
                return price_unit
            else:
                line.product_qty = 0
        elif quantity > 0:
            line = self.env[self._get_line_model()].create(
                {
                    "order_id": self.id,
                    "product_id": product_id,
                    "product_qty": quantity,
                    "sequence": self._get_new_line_sequence(child_field, section_id),
                },
            )
            self._catalog_on_line_created(line, **kwargs)
        else:
            product = self.env["product.product"].browse(product_id)
            return self._get_catalog_removed_line_price(product, **kwargs)
        return self._get_catalog_line_price(line)

    def _update_catalog_context(self):
        return

    def _get_catalog_editable_states(self):
        return {"draft"}

    def _get_catalog_removed_line_price(self, product, **kwargs):
        raise NotImplementedError(
            f"{self._name} must implement _get_catalog_removed_line_price()"
        )

    def _get_catalog_line_price(self, line):
        raise NotImplementedError(
            f"{self._name} must implement _get_catalog_line_price()"
        )

    def _catalog_on_line_created(self, line, **kwargs):
        return line

    def _get_edi_builders(self):
        return []

    def _get_edi_filename(self, builder):
        self.check_singleton()
        return builder._export_invoice_filename(self)

    def create_document_from_attachment(self, attachment_ids):
        attachments = self.env["ir.attachment"].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided."))

        orders = self.with_context(
            default_partner_id=self.env.user.partner_id.id,
        )._create_records_from_attachments(attachments)
        return orders._get_records_action(name=_("Generated Orders"))
