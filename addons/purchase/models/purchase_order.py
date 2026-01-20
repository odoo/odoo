from collections import defaultdict
from dateutil.relativedelta import relativedelta
from markupsafe import escape, Markup
from pytz import timezone
from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import (
    format_amount,
    format_date,
    format_list,
    formatLang,
    groupby,
    OrderedSet,
    SQL,
)
from odoo.tools.float_utils import float_repr
from odoo.tools.translate import _

from odoo.addons.purchase import const


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = [
        "account.document.import.mixin",
        "mail.activity.mixin",
        "mail.thread",
        "portal.mixin",
        "product.catalog.mixin",
    ]
    _description = "Purchase Order"
    _check_company_auto = True
    _rec_names_search = ["name", "partner_ref"]
    _order = "priority desc, id desc"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company.id,
        index=True,
    )
    company_price_include = fields.Selection(
        related="company_id.account_price_include",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        change_default=True,
        check_company=True,
        index=True,
        tracking=True,
        help="You can find a vendor by its Name, TIN, Email or Internal Reference.",
    )
    commercial_partner_id = fields.Many2one(
        related="partner_id.commercial_partner_id",
        store=True,
        index=True,
    )
    partner_bill_count = fields.Integer(
        related="partner_id.supplier_invoice_count",
    )
    dest_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Dropship Address",
        check_company=True,
        index=True,
        tracking=True,
        help="Put an address if you want to deliver directly from the vendor to the customer. "
        "Otherwise, keep empty to deliver to your own company.",
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        compute="_compute_fiscal_position_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        domain='[("company_id", "in", (False, company_id))]',
        help="Fiscal positions are used to adapt taxes and accounts for particular customers "
        "or sales orders/invoices. The default value comes from the customer.",
    )
    incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Incoterm",
        help="International Commercial Terms are a series of predefined commercial terms used in international transactions.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        compute="_compute_currency_id",
        store=True,
        precompute=True,
        readonly=False,
        ondelete="restrict",
    )
    currency_rate = fields.Float(
        string="Currency Rate",
        digits=0,
        compute="_compute_currency_rate",
        store=True,
        precompute=True,
    )
    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        compute="_compute_payment_term_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        domain="[('company_id', 'in', [False, company_id])]",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Buyer",
        compute="_compute_user_id",
        store=True,
        precompute=True,
        readonly=False,
        domain=lambda self: """
            [
                ('all_group_ids', 'in', {}),
                ('share', '=', False),
                ('company_ids', '=', company_id),
            ]
        """.format(
            self.env.ref("purchase.group_purchase_user").ids,
        ),
        index=True,
        tracking=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Billing Journal",
        compute="_compute_journal_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        domain=[("type", "=", "purchase")],
        help="If set, the PO will invoice in this journal; "
        "otherwise the purchase journal with the lowest sequence is used.",
    )
    name = fields.Char(
        string="Order Reference",
        required=True,
        default=lambda self: _("New"),
        readonly=True,
        copy=False,
        index="trigram",
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Status",
        default="draft",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    priority = fields.Selection(
        selection=[
            ("0", "Normal"),
            ("1", "Urgent"),
        ],
        string="Priority",
        default="0",
        index=True,
    )
    date_order = fields.Datetime(
        string="Order Deadline",
        required=True,
        default=fields.Datetime.now,
        copy=False,
        index=True,
        help="Depicts the date within which the Quotation should be "
        "confirmed and converted into a purchase order.",
    )
    date_validity = fields.Date(
        string="Expiration",
        # compute="_compute_date_validity",
        # store=True,
        # precompute=True,
        readonly=False,
        copy=False,
        help="Validity of the order, after that you will not able to sign & pay the quotation.",
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        readonly=True,
        copy=False,
        index=True,
        help="Date when the purchase order was confirmed.",
    )
    date_calendar_start = fields.Datetime(
        compute="_compute_date_calendar_start",
        store=True,
        readonly=True,
    )

    # Order line block
    line_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="order_id",
        string="Order Lines",
        copy=True,
    )
    product_id = fields.Many2one(
        related="line_ids.product_id",
        comodel_name="product.product",
        string="Product",
    )
    date_planned = fields.Datetime(
        string="Expected Arrival",
        compute="_compute_date_planned",
        store=True,
        readonly=False,
        copy=False,
        index=True,
        help="Delivery date promised by vendor. "
        "This date is used to determine expected arrival of products.",
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amounts",
        store=True,
        readonly=True,
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        compute="_compute_amounts",
        store=True,
        readonly=True,
        tracking=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        readonly=True,
        tracking=True,
    )
    tax_totals = fields.Binary(
        compute="_compute_tax_totals",
        exportable=False,
    )

    # Invoice block
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Bills",
        compute="_compute_invoice_ids",
        search="_search_invoice_ids",
    )
    invoice_count = fields.Integer(
        string="Bill Count",
        compute="_compute_invoice_ids",
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Incl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxexc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Excl.)",
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
    invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Invoice status",
        default="no",
        compute="_compute_invoice_state",
        store=True,
        copy=False,
    )

    origin = fields.Char(
        string="Source",
        copy=False,
        help="Reference of the document that generated this purchase order "
        "request (e.g. a sales order)",
    )
    partner_ref = fields.Char(
        string="Vendor Reference",
        copy=False,
        help="Reference of the sales order or bid sent by the vendor. "
        "It's used to do the matching when you receive the "
        "products as this reference is usually written on the "
        "delivery order sent by your vendor.",
    )
    notes = fields.Html(string="Terms and Conditions")
    acknowledged = fields.Boolean(
        string="Acknowledged",
        copy=False,
        tracking=True,
        help="It indicates that the vendor has acknowledged the receipt of the purchase order.",
    )
    locked = fields.Boolean(
        default=False,
        copy=False,
        tracking=True,
        help="Locked orders cannot be modified.",
    )
    sent = fields.Boolean(
        default=False,
        copy=False,
        tracking=True,
        help="THE Quotation has been sent to the customer.",
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
        help="THE RFQ has already been printed.",
    )
    count_print = fields.Integer(
        string="Print Count",
        default=0,
        copy=False,
    )
    is_late = fields.Boolean(
        string="Is Late",
        store=False,
        search="_search_is_late",
    )
    show_comparison = fields.Boolean(
        string="Show Comparison",
        compute="_compute_show_comparison",
    )
    type_name = fields.Char(
        string="Type Name",
        compute="_compute_type_name",
    )
    purchase_warning_text = fields.Text(
        string="Purchase Warning",
        compute="_compute_purchase_warning_text",
        help="Internal warning for the partner or the products as set by the user.",
    )
    duplicated_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        compute="_compute_duplicated_order_ids",
    )
    receipt_reminder_email = fields.Boolean(
        string="Receipt Reminder Email",
        compute="_compute_receipt_reminder_email",
        store=True,
        readonly=False,
    )
    reminder_date_before_receipt = fields.Integer(
        string="Days Before Receipt",
        compute="_compute_receipt_reminder_email",
        store=True,
        readonly=False,
    )

    # ------------------------------------------------------------
    # CONSTRAINTS
    # ------------------------------------------------------------

    @api.constrains("company_id", "line_ids")
    def _check_line_ids_company_id(self):
        for order in self:
            invalid_companies = order.line_ids.product_id.company_id.filtered(
                lambda c: order.company_id not in c._accessible_branches(),
            )
            if invalid_companies:
                bad_products = order.line_ids.product_id.filtered(
                    lambda p: p.company_id and p.company_id in invalid_companies,
                )
                raise ValidationError(
                    _(
                        """Your quotation contains products from company %(product_company)s whereas
                        your quotation belongs to company %(quote_company)s. \n
                        Please change the company of your quotation or remove the products from
                        other companies (%(bad_products)s).""",
                        product_company=", ".join(
                            invalid_companies.sudo().mapped("display_name"),
                        ),
                        quote_company=order.company_id.display_name,
                        bad_products=", ".join(bad_products.mapped("display_name")),
                    ),
                )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company_id = vals.get(
                "company_id",
                self.default_get(["company_id"])["company_id"],
            )
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get("name", _("New")) == _("New"):
                date_order = vals.get(
                    "date_order",
                    self_comp.default_get(["date_order"])["date_order"],
                )
                seq_date = fields.Datetime.context_timestamp(
                    self_comp,
                    fields.Datetime.to_datetime(date_order),
                )
                vals["name"] = self_comp.env["ir.sequence"].next_by_code(
                    "purchase.order",
                    sequence_date=seq_date,
                )
        return super().create(vals_list)

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.pop("default_product_id", None)
        self = self.with_context(ctx)
        new_orders = super().copy(default=default)
        for line in new_orders.line_ids:
            if line.product_id:
                line.date_planned = line._get_date_planned(line.selected_seller_id)
        return new_orders

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for order in self:
            if order.state not in ("draft", "cancel"):
                raise UserError(
                    _(
                        "You can not delete a confirmed orders. "
                        "You must cancel it first.",
                    ),
                )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_access_url(self):
        super()._compute_access_url()
        for order in self:
            order.access_url = f"/my/purchase/{order.id}"

    def _compute_journal_id(self):
        self.journal_id = False

    @api.depends("state")
    def _compute_type_name(self):
        for order in self:
            if order.state in ("draft", "cancel"):
                order.type_name = _("Quotation")
            else:
                order.type_name = _("Purchase Order")

    @api.depends("state", "date_order", "date_confirmed")
    def _compute_date_calendar_start(self):
        """
        Compute calendar start date for purchase order.

        Uses date_confirmed when order is confirmed (purchase state),
        otherwise uses date_order.

        :return: None (sets date_calendar_start field)
        """
        for order in self:
            order.date_calendar_start = (
                order.date_confirmed if order.state == "done" else order.date_order
            )

    @api.depends("partner_id")
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = order.partner_id.property_supplier_payment_term_id

    @api.depends("partner_id")
    def _compute_user_id(self):
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                # Recompute the buyer on partner change
                #   * if partner is set (is required anyway, so it will be set sooner or later)
                #   * if the order is not saved or has no buyer already
                order.user_id = (
                    order.partner_id.user_purchase_id
                    or order.commercial_partner_id.user_purchase_id
                    or (
                        self.env.user.has_group("purchase.group_purchase_user")
                        and self.env.user
                    )
                )

    @api.depends("partner_id", "partner_ref", "origin")
    def _compute_duplicated_order_ids(self):
        """Compute duplicated purchase orders based on key fields."""
        draft_orders = self.filtered(lambda o: o.state == "draft")
        order_to_duplicate_orders = draft_orders._get_duplicate_orders()
        for order in draft_orders:
            duplicate_ids = order_to_duplicate_orders.get(order.id, [])
            order.duplicated_order_ids = [Command.set(duplicate_ids)]
        (self - draft_orders).duplicated_order_ids = False

    @api.depends("company_id", "partner_id")
    def _compute_currency_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.currency_id = (
                order.partner_id.property_purchase_currency_id
                or order.company_id.currency_id
            )

    @api.depends("company_id", "currency_id", "date_order")
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(order.date_order or fields.Datetime.now()).date(),
            )

    @api.depends("company_id", "partner_id")
    def _compute_fiscal_position_id(self):
        """Trigger the change of fiscal position when the shipping address is modified."""
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue

            # fpos_id_before = order.fiscal_position_id.id
            key = (
                order.company_id.id,
                order.partner_id.id,
                # order.partner_shipping_id.id,
            )
            if key not in cache:
                cache[key] = (
                    self.env["account.fiscal.position"]
                    .with_company(order.company_id)
                    ._get_fiscal_position(order.partner_id)
                    .id
                )
            # if fpos_id_before != cache[key] and order.line_ids:
            #     order.show_update_fpos = True
            order.fiscal_position_id = cache[key]

    @api.depends("company_id", "partner_id", "partner_id.reminder_date_before_receipt")
    def _compute_receipt_reminder_email(self):
        for order in self:
            order.receipt_reminder_email = order.partner_id.with_company(
                order.company_id,
            ).receipt_reminder_email
            order.reminder_date_before_receipt = order.partner_id.with_company(
                order.company_id,
            ).reminder_date_before_receipt

    @api.depends("line_ids", "line_ids.date_planned")
    def _compute_date_planned(self):
        """date_planned = the earliest date_planned across all order lines."""
        for order in self:
            if order.state == "cancel":
                order.date_planned = False
                continue

            dates_list = order.line_ids.filtered(
                lambda line: not line.display_type and line.date_planned,
            ).mapped("date_planned")
            if dates_list:
                order.date_planned = min(dates_list)
            else:
                order.date_planned = False

    @api.depends("line_ids", "line_ids.product_id")
    def _compute_show_comparison(self):
        line_groupby_product = self.env["purchase.order.line"]._read_group(
            [
                ("product_id", "in", self.line_ids.product_id.ids),
                ("state", "=", "done"),
            ],
            ["product_id"],
            ["order_id:array_agg"],
        )
        order_by_product = {p: set(o_ids) for p, o_ids in line_groupby_product}
        for order in self:
            order.show_comparison = any(
                set(order.ids) != order_by_product[p]
                for p in order.line_ids.product_id
                if p in order_by_product
            )

    @api.depends("company_id", "currency_id", "line_ids.price_subtotal")
    def _compute_amounts(self):
        AccountTax = self.env["account.tax"]
        for order in self:
            order_lines = order.line_ids.filtered(lambda line: not line.display_type)
            base_lines = [
                line._prepare_base_line_for_taxes_computation() for line in order_lines
            ]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            order.amount_untaxed = tax_totals["base_amount_currency"]
            order.amount_tax = tax_totals["tax_amount_currency"]
            order.amount_total = tax_totals["total_amount_currency"]

    @api.depends_context("lang")
    @api.depends("company_id", "currency_id", "line_ids.price_subtotal")
    def _compute_tax_totals(self):
        AccountTax = self.env["account.tax"]
        for order in self:
            order_lines = order.line_ids.filtered(lambda line: not line.display_type)
            base_lines = [
                line._prepare_base_line_for_taxes_computation() for line in order_lines
            ]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            order.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )

    @api.depends(
        "line_ids.amount_taxexc_invoiced",
        "line_ids.amount_taxexc_to_invoice",
        "line_ids.amount_taxinc_invoiced",
        "line_ids.amount_taxinc_to_invoice",
    )
    def _compute_amounts_invoice(self):
        for order in self:
            order.amount_taxexc_invoiced = sum(
                order.line_ids.mapped("amount_taxexc_invoiced"),
            )
            order.amount_taxexc_to_invoice = sum(
                order.line_ids.mapped("amount_taxexc_to_invoice"),
            )
            order.amount_taxinc_invoiced = sum(
                order.line_ids.mapped("amount_taxinc_invoiced"),
            )
            order.amount_taxinc_to_invoice = sum(
                order.line_ids.mapped("amount_taxinc_to_invoice"),
            )

    @api.depends_context("show_total_amount")
    @api.depends("currency_id", "name", "partner_ref", "amount_total")
    def _compute_display_name(self):
        for order in self:
            name = order.name
            if order.partner_ref:
                name += " (" + order.partner_ref + ")"
            if self.env.context.get("show_total_amount") and order.amount_total:
                name += ": " + formatLang(
                    self.env,
                    order.amount_total,
                    currency_obj=order.currency_id,
                )
            order.display_name = name

    @api.depends(
        "partner_id.name",
        "partner_id.purchase_warn_msg",
        "line_ids.purchase_line_warn_msg",
    )
    def _compute_purchase_warning_text(self):
        if not self.env.user.has_group("purchase.group_warning_purchase"):
            self.purchase_warning_text = ""
            return
        for order in self:
            warnings = OrderedSet()
            if partner_msg := order.partner_id.purchase_warn_msg:
                warnings.add(
                    (order.partner_id.name or order.partner_id.display_name)
                    + " - "
                    + partner_msg,
                )
            if partner_parent_msg := order.partner_id.parent_id.purchase_warn_msg:
                parent = order.partner_id.parent_id
                warnings.add(
                    (parent.name or parent.display_name) + " - " + partner_parent_msg
                )
            for line in order.line_ids:
                if product_msg := line.purchase_line_warn_msg:
                    warnings.add(line.product_id.display_name + " - " + product_msg)
            order.purchase_warning_text = "\n".join(warnings)

    @api.depends(
        "line_ids.invoice_line_ids",
        "line_ids.invoice_line_ids.move_id.reversal_move_ids",
    )
    def _compute_invoice_ids(self):
        """Compute invoice_ids for the sale order.

        The invoice_ids are obtained from:
        1. Invoice lines directly linked to SO lines
        2. Refunds created directly from existing invoices (not linked to SO)

        This is necessary since refunds created via "Credit Note" button on an
        invoice are not directly linked to the original SO.
        """
        for order in self:
            # Get directly linked invoices
            invoices = order.line_ids.invoice_line_ids.move_id.filtered(
                lambda r: r.move_type in ("in_invoice", "in_refund"),
            )

            # Search for refunds created from these invoices that aren't already linked
            # These are "orphan" refunds created via the Credit Note button
            if invoices:
                orphan_refunds = self.env["account.move"].search(
                    [
                        ("reversed_entry_id", "in", invoices.ids),
                        ("move_type", "=", "in_refund"),
                        ("id", "not in", invoices.ids),  # Exclude already found refunds
                    ]
                )
                invoices |= orphan_refunds

            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    @api.depends("state", "line_ids.invoice_state")
    def _compute_invoice_state(self):
        confirmed_orders = self.filtered(lambda order: order.state == "done")
        (self - confirmed_orders).invoice_state = "no"
        if not confirmed_orders:
            return

        for order in confirmed_orders:
            line_states = set(
                order.line_ids.filtered(lambda l: not l.display_type).mapped(
                    "invoice_state"
                )
            )

            if not line_states or line_states == {"no"}:
                order.invoice_state = "no"
            elif "over done" in line_states:
                order.invoice_state = "over done"
            elif "to do" in line_states:
                order.invoice_state = "to do"
            elif "partial" in line_states:
                order.invoice_state = "partial"
            elif line_states == {"done"} or line_states == {"done", "no"}:
                order.invoice_state = "done"
            else:
                order.invoice_state = "no"

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    def _search_invoice_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if operator == "in" and value:
            falsy_domain = []
            if False in value:
                # special case for [('invoice_ids', '=', False)], i.e. "Invoices is not set"
                #
                # We cannot just search [('line_ids.invoice_line_ids', '=', False)]
                # because it returns orders with uninvoiced lines, which is not
                # same "Invoices is not set" (some lines may have invoices and some
                # don't)
                #
                # A solution is using the 'not any' operators with inverted search first
                # ("orders with invoiced lines").
                falsy_domain = [
                    (
                        "line_ids",
                        "not any",
                        [
                            (
                                "invoice_line_ids.move_id.move_type",
                                "in",
                                ("in_invoice", "in_refund"),
                            ),
                        ],
                    ),
                ]
                if len(value) == 1:
                    return falsy_domain
            self.env.cr.execute(
                """
                SELECT array_agg(o.id)
                    FROM purchase_order o
                    JOIN purchase_order_line ol ON o.id=ol.order_id
                    JOIN account_move_line_purchase_order_line_rel soli_rel ON soli_rel.order_line_id = ol.id
                    JOIN account_move_line aml ON aml.id = soli_rel.invoice_line_id
                    JOIN account_move am ON am.id = aml.move_id
                WHERE
                    am.move_type in ('in_invoice', 'in_refund')
                    AND am.id = ANY(%s)
                """,
                (list(value),),
            )
            o_ids = self.env.cr.fetchone()[0] or []
            return [("id", "in", o_ids)] + falsy_domain
        return [
            (
                "line_ids.invoice_line_ids",
                "any",
                [
                    ("move_id.move_type", "in", ("in_invoice", "in_refund")),
                    ("move_id", operator, value),
                ],
            ),
        ]

    def _search_is_late(self, operator, value):
        if operator not in ["=", "!="]:
            raise ValidationError(self.env._("Unsupported operator"))

        purchase_domain = self._get_domain_is_late(operator, value)

        if operator == "=" and value or operator == "!=" and not value:
            purchase_lines_late = Domain(
                "order_id", "any", purchase_domain
            ) & Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "%s < %s",
                    model._field_to_sql(alias, "qty_received", query),
                    model._field_to_sql(alias, "product_qty", query),
                ),
            )
            return Domain("line_ids", "any", purchase_lines_late)
        else:
            purchase_lines_on_time = Domain(
                "order_id", "any", purchase_domain
            ) & Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    "%s >= %s",
                    model._field_to_sql(alias, "qty_received", query),
                    model._field_to_sql(alias, "product_qty", query),
                ),
            )
            return Domain("line_ids", "any", purchase_lines_on_time)

    # ------------------------------------------------------------
    # ONCHANGE METHODS
    # ------------------------------------------------------------

    def onchange(self, values, field_names, fields_spec):
        """
        Override onchange to NOT update all date_planned on PO lines when
        date_planned on PO is updated by the change of date_planned on PO lines.
        """
        result = super().onchange(values, field_names, fields_spec)
        if (
            any(self._must_delete_date_planned(field) for field in field_names)
            and "value" in result
        ):
            for line in result["value"].get("line_ids", []):
                if line[0] == Command.UPDATE and "date_planned" in line[2]:
                    del line[2]["date_planned"]
        return result

    @api.onchange("partner_id", "company_id")
    def onchange_partner_id(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.fiscal_position_id = False
        else:
            self.fiscal_position_id = self.env[
                "account.fiscal.position"
            ]._get_fiscal_position(self.partner_id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            if self.partner_id.user_purchase_id:
                self.user_id = self.partner_id.user_purchase_id
        return {}

    @api.onchange("date_planned")
    def _onchange_date_planned(self):
        if self.date_planned:
            self.line_ids.filtered(
                lambda line: not line.display_type,
            ).date_planned = self.date_planned

    @api.onchange("company_id", "fiscal_position_id")
    def _onchange_fiscal_position_id(self):
        """Trigger the recompute of the taxes if the fiscal position is changed"""
        self.line_ids._compute_tax_ids()

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_acknowledge(self):
        self.write({"acknowledged": True})

    def action_bill_matching(self):
        self.ensure_one()
        return {
            "name": _("Bill Matching"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.bill.line.match",
            "views": [
                (self.env.ref("purchase.purchase_bill_line_match_tree").id, "list"),
            ],
            "domain": [
                ("company_id", "in", self.env.company.ids),
                (
                    "partner_id",
                    "in",
                    (self.partner_id | self.partner_id.commercial_partner_id).ids,
                ),
                ("purchase_order_id", "in", [self.id, False]),
            ],
        }

    def action_cancel(self):
        """Cancel purchase orders and their draft invoices.

        Validates cancellation is allowed before proceeding. Draft invoices
        related to these orders are also cancelled automatically.

        :raises UserError: If orders cannot be cancelled (locked, have posted bills, etc.)
        :return: True for backwards compatibility
        :rtype: bool
        """
        # Validate all orders upfront before any modifications
        self._can_cancel()

        # Cancel related draft invoices (if any)
        draft_invoices = self.invoice_ids.filtered(lambda inv: inv.state == "draft")
        if draft_invoices:
            draft_invoices.button_cancel()

        # Update state to cancelled
        self.write({"state": "cancel"})

        return True

    def action_confirm(self):
        """Confirm purchase orders.

        Validates orders can be confirmed and transitions them to purchase state.

        Note: Approval workflow is handled by approval_purchase module if installed.
        This method only handles the core confirmation logic.

        :raises UserError: If order cannot be confirmed
        :return: True
        """
        self._can_confirm()
        for order in self:
            order._create_supplier_to_product()
            order.write(
                {
                    "state": "done",
                    "date_confirmed": fields.Datetime.now(),
                },
            )
            if order._should_be_locked():
                order.action_lock()
        return True

    def action_draft(self):
        self.write({"state": "draft"})

    def action_lock(self):
        """Lock purchase orders to prevent modifications."""
        self.write({"locked": True, "priority": "0"})

    def action_unlock(self):
        """Unlock purchase orders to allow modifications."""
        self.write({"locked": False})

    def action_merge(self):
        all_origin = []
        all_vendor_references = []
        rfq_to_merge = self.filtered(lambda r: r.state in ["draft", "sent"])

        if len(rfq_to_merge) < 2:
            raise UserError(
                _(
                    "Please select at least two purchase orders with state RFQ and RFQ sent to merge.",
                ),
            )

        rfqs_grouped = defaultdict(lambda: self.env["purchase.order"])
        for rfq in rfq_to_merge:
            key = self._prepare_grouped_data(rfq)
            rfqs_grouped[key] += rfq

        bunches_of_rfq_to_be_merge = list(rfqs_grouped.values())
        if all(len(rfq_bunch) == 1 for rfq_bunch in list(bunches_of_rfq_to_be_merge)):
            raise UserError(
                _(
                    "In selected purchase order to merge these details must be same\nVendor, currency, destination, dropship address and agreement",
                ),
            )

        bunches_of_rfq_to_be_merge = [
            rfqs for rfqs in bunches_of_rfq_to_be_merge if len(rfqs) > 1
        ]

        merged_rfq_ids = []

        for rfqs in bunches_of_rfq_to_be_merge:
            if len(rfqs) <= 1:
                continue

            oldest_rfq = min(rfqs, key=lambda r: r.date_order)
            if oldest_rfq:
                # Merge RFQs into the oldest purchase order
                rfqs -= oldest_rfq
                for rfq_line in rfqs.line_ids:
                    existing_line = oldest_rfq.line_ids.filtered(
                        lambda l: l.display_type
                        not in ["line_section", "line_subsection", "line_note"]
                        and l.product_id == rfq_line.product_id
                        and l.product_uom_id == rfq_line.product_uom_id
                        and l.analytic_distribution == rfq_line.analytic_distribution
                        and l.discount == rfq_line.discount
                        and abs(l.date_planned - rfq_line.date_planned).total_seconds()
                        <= 86400,  # 24 hours in seconds
                    )
                    if len(existing_line) > 1:
                        existing_line[0].product_qty += sum(
                            existing_line[1:].mapped("product_qty"),
                        )
                        existing_line[1:].unlink()
                        existing_line = existing_line[0]

                    if existing_line:
                        existing_line._merge_po_line(rfq_line)
                    else:
                        rfq_line.order_id = oldest_rfq

                # Merge source documents and vendor references
                all_origin = rfqs.mapped("origin")
                all_vendor_references = rfqs.mapped("partner_ref")
                oldest_rfq.origin = ", ".join(
                    filter(None, [oldest_rfq.origin, *all_origin]),
                )
                oldest_rfq.partner_ref = ", ".join(
                    filter(None, [oldest_rfq.partner_ref, *all_vendor_references]),
                )
                rfq_names = rfqs.mapped("name")
                merged_names = ", ".join(rfq_names)
                oldest_rfq_message = _(
                    "RFQ merged with %(oldest_rfq_name)s and %(cancelled_rfq)s",
                    oldest_rfq_name=oldest_rfq.name,
                    cancelled_rfq=merged_names,
                )
                for rfq in rfqs:
                    cancelled_rfq_message = _(
                        "RFQ merged with %s",
                        oldest_rfq._get_html_link(),
                    )
                    rfq.message_post(body=cancelled_rfq_message)
                oldest_rfq.message_post(body=oldest_rfq_message)
                rfqs.filtered(lambda r: r.state != "cancel").action_cancel()
                oldest_rfq._merge_alternative_po(rfqs)

                # Keep the oldest RFQ IDs
                merged_rfq_ids.append(oldest_rfq.id)

        action = {
            "type": "ir.actions.act_window",
            "view_mode": "list,kanban,form",
            "res_model": "purchase.order",
        }
        if len(merged_rfq_ids) == 1:
            action["res_id"] = merged_rfq_ids[0]
            action["view_mode"] = "form"
        else:
            action["name"] = _("Merged RFQs")
            action["domain"] = [("id", "in", merged_rfq_ids)]
        return action

    def action_print_quotation(self):
        self.filtered(lambda order: order.state == "draft").write(
            {"printed_before": True},
        )
        return self.env.ref("purchase.report_purchase_quotation").report_action(self)

    def action_purchase_comparison(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.action_purchase_history",
        )
        action["display_name"] = _(f"Purchase Comparison for {self.display_name}")
        action["domain"] = [("product_id", "in", self.line_ids.product_id.ids)]
        return action

    def action_send_rfq(self):
        """
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        """
        self.ensure_one()
        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "default_model": "purchase.order",
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                "email_notification_allow_footer": True,
                "force_email": True,
                "hide_mail_template_management_options": True,
                "mark_rfq_as_sent": True,
                "model_description": _(self.type_name),
            },
        )
        template_id = self._get_mail_template()
        if template_id:
            ctx.update({"default_template_id": template_id})
        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get("lang")
        if {"default_template_id", "default_model", "default_res_id"} <= ctx.keys():
            template = self.env["mail.template"].browse(template_id)
            if template and template.lang:
                lang = template._render_lang([ctx["default_res_id"]])[
                    ctx["default_res_id"]
                ]
        self = self.with_context(lang=lang)
        compose_form_id = self._get_mail_compose_form()
        return {
            "name": _("Compose Email"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def action_view_business_doc(self):
        self.ensure_one()
        return {
            "name": _("Order"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": self.id,
            "views": [(False, "form")],
        }

    def action_view_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            self.invalidate_model(["invoice_ids"])
            invoices = self.invoice_ids

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_in_invoice_type",
        )

        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref("account.view_move_form", False)
            form_view = [(res and res.id or False, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = invoices.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {
            "default_move_type": "in_invoice",
        }
        if len(self) == 1:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "default_invoice_payment_term_id": self.payment_term_id.id
                    or self.partner_id.property_supplier_payment_term_id.id
                    or self.env["account.move"]
                    .default_get(["invoice_payment_term_id"])
                    .get("invoice_payment_term_id"),
                    "default_invoice_origin": self.name,
                },
            )
        action["context"] = context
        return action

    # ------------------------------------------------------------
    # MAIL METHODS
    # ------------------------------------------------------------

    def _create_update_date_activity(self, updated_dates):
        note = Markup("<p>%s</p>\n") % _(
            "%s modified receipt dates for the following products:",
            self.partner_id.name,
        )
        for line, date in updated_dates:
            note += Markup("<p> - %s</p>\n") % _(
                "%(product)s from %(original_receipt_date)s to %(new_receipt_date)s",
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date(),
            )
        activity = self.activity_schedule(
            "mail.mail_activity_data_warning",
            summary=_("Date Updated"),
            user_id=self.user_id.id,
        )
        # add the note after we post the activity because the note can be soon
        # changed when updating the date of the next PO line. So instead of
        # sending a mail with incomplete note, we send one with no note.
        activity.note = note
        return activity

    def message_post(self, **kwargs):
        if self.env.context.get("mark_rfq_as_sent"):
            self.filtered(lambda order: order.state == "draft").write({"sent": True})
            kwargs["notify_author_mention"] = kwargs.get("notify_author_mention", True)
        return super().message_post(**kwargs)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        # Tweak "view document" button for portal customers,
        # calling directly routes for confirm specific to PO model.
        groups = super()._notify_get_recipients_groups(
            message,
            model_description,
            msg_vals=msg_vals,
        )
        if not self:
            return groups

        self.ensure_one()
        try:
            customer_portal_group = next(
                group for group in groups if group[0] == "portal_customer"
            )
        except StopIteration:
            pass

        else:
            access_opt = customer_portal_group[2].setdefault("button_access", {})
            if self.env.context.get("is_reminder"):
                access_opt["title"] = _("View")
            else:
                access_opt.update(
                    title=_("View" + " " + self.type_name),
                    url=self.get_base_url() + self.get_confirm_url(),
                )
        return groups

    def _notify_by_email_prepare_rendering_context(
        self,
        message,
        msg_vals=False,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        force_record_name=False,
    ):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
        )
        subtitles = [render_context["record"].name]
        # don't show price on RFQ mail
        if self.state == "draft":
            subtitles.append(
                _(
                    "Order\N{NO-BREAK SPACE}due\N{NO-BREAK SPACE}%(date)s",
                    date=format_date(
                        self.env,
                        self.date_order,
                        lang_code=render_context.get("lang"),
                    ),
                ),
            )
        else:
            subtitles.append(
                format_amount(
                    self.env,
                    self.amount_total,
                    self.currency_id,
                    lang_code=render_context.get("lang"),
                ),
            )
        render_context["subtitles"] = subtitles
        return render_context

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "state" in init_values and self.state == "done":
            if init_values["state"] == "to approve":
                return self.env.ref("purchase.mt_rfq_approved")

            return self.env.ref("purchase.mt_rfq_confirmed")

        elif "state" in init_values and self.state == "to approve":
            return self.env.ref("purchase.mt_rfq_confirmed")

        elif "locked" in init_values and self.locked:
            return self.env.ref("purchase.mt_rfq_done")

        elif "sent" in init_values and self.sent:
            return self.env.ref("purchase.mt_rfq_sent")

        return super()._track_subtype(init_values)

    def _update_update_date_activity(self, updated_dates, activity):
        for line, date in updated_dates:
            activity.note += Markup("<p> - %s</p>\n") % _(
                "%(product)s from %(original_receipt_date)s to %(new_receipt_date)s",
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date(),
            )

    # ------------------------------------------------------------
    # CATALOGUE MIXIN METHODS
    # ------------------------------------------------------------

    def action_add_from_catalog(self):
        res = super().action_add_from_catalog()
        kanban_view_id = self.env.ref(
            "purchase.product_view_kanban_catalog_purchase_only",
        ).id
        res["views"][0] = (kanban_view_id, "kanban")
        res["search_view_id"] = [
            self.env.ref("purchase.product_view_search_catalog").id,
            "search",
        ]
        res["context"]["partner_id"] = self.partner_id.id
        return res

    def _default_order_line_values(self, child_field=False):
        default_data = super()._default_order_line_values(child_field)
        new_default_data = self.env[
            "purchase.order.line"
        ]._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            "precision": self.env["decimal.precision"].precision_get("Product Unit"),
            "product_catalog_currency_id": self.currency_id.id,
            "product_catalog_digits": self.line_ids._fields["price_unit"].get_digits(
                self.env,
            ),
            "search_default_seller_ids": self.partner_id.name,
            "show_sections": bool(self.id),
        }

    def _get_parent_field_on_child_model(self):
        return "order_id"

    def _get_product_catalog_domain(self):
        return super()._get_product_catalog_domain() & Domain("purchase_ok", "=", True)

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            res[product.id] |= self._get_product_price_and_data(product)
        return res

    def _get_product_catalog_record_lines(
        self,
        product_ids,
        *,
        section_id=None,
        **kwargs,
    ):
        grouped_lines = defaultdict(lambda: self.env["purchase.order.line"])
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
        return grouped_lines

    def _is_readonly(self):
        """Return whether the purchase order is read-only or not based on the state.
        A purchase order is considered read-only if its state is 'cancel'.

        :return: Whether the purchase order is read-only or not.
        :rtype: bool
        """
        self.ensure_one()
        return self.state == "cancel"

    def _update_order_line_info(
        self,
        product_id,
        quantity,
        *,
        section_id=False,
        child_field="line_ids",
        **kwargs,
    ):
        """Update purchase order line information for a given product or create
        a new one if none exists yet.
        :param int product_id: The product, as a `product.product` id.
        :param int quantity: The quantity selected in the catalog.
        :param int section_id: The id of section selected in the catalog.
        :return: The unit price of the product, based on the pricelist of the
                 purchase order and the quantity selected.
        :rtype: float
        """
        self.ensure_one()
        pol = self.line_ids.filtered(
            lambda l: l.product_id.id == product_id
            and l.get_line_parent_section().id == section_id,
        )
        if pol:
            if quantity != 0:
                pol.product_qty = quantity
            elif self.state in ["draft", "sent"]:
                price_unit = self._get_product_price_and_data(pol.product_id)["price"]
                pol.unlink()
                return price_unit
            else:
                pol.product_qty = 0
        elif quantity > 0:
            pol = self.env["purchase.order.line"].create(
                {
                    "order_id": self.id,
                    "product_id": product_id,
                    "product_qty": quantity,
                    "sequence": self._get_new_line_sequence(child_field, section_id),
                },
            )
            if pol.selected_seller_id:
                # Fix the PO line's price on the seller's one.
                seller = pol.selected_seller_id
                price = seller.price
                if seller.currency_id != self.currency_id:
                    price = seller.currency_id._convert(price, self.currency_id)
                pol.price_unit = pol.price_unit_shadow = price
                pol.discount = seller.discount
        return pol.price_unit_discounted_taxexc

    # ------------------------------------------------------------
    # PRODUCT DOCUMENTS METHODS
    # ------------------------------------------------------------

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Requests for Quotation"),
                "template": "/purchase/static/xls/requests_for_quotation_import_template.xlsx",
            },
        ]

    # ------------------------------------------------------------
    # EDI METHODS
    # ------------------------------------------------------------

    def _get_edi_builders(self):
        return []

    def create_document_from_attachment(self, attachment_ids):
        """Create the purchase orders from given attachment_ids
        and redirect newly create order view.

        :param list attachment_ids: List of attachments process.
        :return: An action redirecting to related sale order view.
        :rtype: dict
        """
        attachments = self.env["ir.attachment"].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        orders = self.with_context(
            default_partner_id=self.env.user.partner_id.id,
        )._create_records_from_attachments(attachments)
        return orders._get_records_action(name=_("Generated Orders"))

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _create_downpayments(self, line_vals):
        self.ensure_one()

        # create section
        if not any(line.display_type and line.is_downpayment for line in self.line_ids):
            section_line = self.line_ids.create(
                self._prepare_down_payment_section_vals(),
            )
        else:
            section_line = self.line_ids.filtered(
                lambda line: line.display_type and line.is_downpayment,
            )
        vals = [
            {
                **line_val,
                "sequence": section_line.sequence + i,
            }
            for i, line_val in enumerate(line_vals, start=1)
        ]
        downpayment_lines = self.env["purchase.order.line"].create(vals)
        # a simple concatenation would cause all line_ids to recompute, we do not want it to happen
        self.line_ids = [Command.link(line_id) for line_id in downpayment_lines.ids]
        return downpayment_lines

    def create_invoice(self, attachment_ids=False):
        """Create the invoice associated to the PO."""
        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10
        for order in self:
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice_vals()
            # Invoice line values (keep only necessary sections).
            for line in order.line_ids:
                if line.display_type in ("line_section", "line_subsection"):
                    pending_section = line
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_aml_vals()
                    line_vals.update({"sequence": sequence})
                    invoice_vals["invoice_line_ids"].append(Command.create(line_vals))
                    sequence += 1
                    pending_section = None
                line_vals = line._prepare_aml_vals()
                line_vals.update({"sequence": sequence})
                invoice_vals["invoice_line_ids"].append(Command.create(line_vals))
                sequence += 1
            invoice_vals_list.append(invoice_vals)

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for _grouping_keys, invoices in groupby(
            invoice_vals_list,
            key=lambda x: (
                x.get("company_id"),
                x.get("partner_id"),
                x.get("currency_id"),
            ),
        ):
            origins = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals["invoice_line_ids"] += invoice_vals[
                        "invoice_line_ids"
                    ]
                origins.add(invoice_vals["invoice_origin"])
            ref_invoice_vals.update(
                {
                    "invoice_origin": ", ".join(origins),
                },
            )
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        invoices = self.env["account.move"]
        AccountMove = self.env["account.move"].with_context(
            default_move_type="in_invoice",
        )
        for vals in invoice_vals_list:
            invoices |= AccountMove.with_company(vals["company_id"]).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        invoices.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0,
        ).action_switch_move_type()

        # 5) Link the attachments to the invoice
        if attachment_ids:
            attachments = self.env["ir.attachment"].browse(attachment_ids)
            if attachments:
                if len(invoices) != 1:
                    raise ValidationError(
                        _("You can only upload a bill for a single vendor at a time."),
                    )
                invoices.with_context(
                    skip_is_manually_modified=True
                )._extend_with_attachments(
                    invoices._to_files_data(attachments),
                    new=True,
                )
                invoices.message_post(attachment_ids=attachments.ids)
                attachments.write({"res_model": "account.move", "res_id": invoices.id})

        return invoices

    def _create_supplier_to_product(self):
        # Add the partner in the supplier list of the product if the supplier is not registered for
        # this product. We limit to 10 the number of suppliers for a product to avoid the mess that
        # could be caused for some generic products ("Miscellaneous").
        for line in self.line_ids:
            # Do not add a contact as a supplier
            partner = (
                self.partner_id
                if not self.partner_id.parent_id
                else self.partner_id.parent_id
            )
            already_seller = (
                partner | self.partner_id
            ) & line.product_id.seller_ids.mapped("partner_id")
            if (
                line.product_id
                and not already_seller
                and len(line.product_id.seller_ids) <= 10
            ):
                price = line.price_unit
                # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
                if line.product_id.product_tmpl_id.uom_id != line.product_uom_id:
                    default_uom = line.product_id.product_tmpl_id.uom_id
                    price = line.product_uom_id._compute_price(price, default_uom)

                supplierinfo = self._prepare_supplierinfo(
                    partner,
                    line,
                    price,
                    line.currency_id,
                )
                # In case the order partner is a contact address, a new supplierinfo is created on
                # the parent company. In this case, we keep the product name and code.
                if line.selected_seller_id:
                    supplierinfo["product_name"] = line.selected_seller_id.product_name
                    supplierinfo["product_code"] = line.selected_seller_id.product_code
                    supplierinfo["product_uom_id"] = line.product_uom.id
                vals = {
                    "seller_ids": [(0, 0, supplierinfo)],
                }
                # supplier info should be added regardless of the user access rights
                line.product_id.product_tmpl_id.sudo().write(vals)

    def get_acknowledge_url(self):
        return self.get_portal_url(query_string="&acknowledge=True")

    def get_confirm_url(self, confirm_type=None):
        """Create url for confirm reminder or purchase reception email for sending
        in mail. Unsuported anymore. We only use the acknowledge mechanism. Keep it
        for backward compatibility"""
        if confirm_type in ["reminder", "reception", "decline"]:
            return self.get_acknowledge_url()
        return self.get_portal_url()

    def _get_default_create_section_values(self):
        """Return the default values for creating a section line in the purchase order through
        catalog.

        :return: A dictionary with default values for creating a new section.
        :rtype: dict
        """
        return {"product_qty": 0}

    def _get_domain_is_late(self, operator, value):
        return Domain(
            [("state", "=", "purchase"), ("date_planned", "<=", fields.Datetime.now())]
        )

    def _get_duplicate_orders(self):
        """Fetch duplicated orders.

        :return: Dictionary mapping order to its related duplicated orders.
        :rtype: dict
        """
        orders = self.filtered(lambda order: order.id and order.partner_ref)
        if not orders:
            return {}

        self.env["purchase.order"].flush_model(
            ["company_id", "partner_id", "partner_ref", "origin", "state"],
        )

        result = self.env.execute_query(
            SQL(
                """
                SELECT
                    po.id AS order_id,
                    array_agg(duplicate_po.id) AS duplicate_ids
                FROM purchase_order po
                JOIN purchase_order AS duplicate_po
                    ON po.company_id = duplicate_po.company_id
                    AND po.id != duplicate_po.id
                    AND duplicate_po.state != 'cancel'
                    AND po.partner_id = duplicate_po.partner_id
                    AND (
                        po.origin = duplicate_po.name
                        OR po.partner_ref = duplicate_po.partner_ref
                    )
                WHERE po.id IN %(orders)s
                GROUP BY po.id
                """,
                orders=tuple(orders.ids),
            ),
        )

        return {order_id: set(duplicate_ids) for order_id, duplicate_ids in result}

    def _get_invoice_grouping_keys(self):
        """Return list of fields to group invoices by.

        Purchase orders are grouped by company, partner, and currency.
        This method can be overridden to customize grouping behavior.

        :return: List of field names for grouping
        :rtype: list[str]
        """
        return ["company_id", "partner_id", "currency_id"]

    def get_localized_date_planned(self, date_planned=False):
        """Returns the localized date planned in the timezone of the order's user or the
        company's partner or UTC if none of them are set."""
        self.ensure_one()
        date_planned = date_planned or self.date_planned
        if not date_planned:
            return False

        if isinstance(date_planned, str):
            date_planned = fields.Datetime.from_string(date_planned)
        tz = self.get_timezone()
        return date_planned.astimezone(tz)

    def _get_mail_compose_form(self):
        ir_model_data = self.env["ir.model.data"]
        try:
            compose_form_id = ir_model_data._xmlid_lookup(
                "mail.email_compose_message_wizard_form",
            )[1]
        except ValueError:
            compose_form_id = False
        return compose_form_id

    def _get_mail_template(self):
        ir_model_data = self.env["ir.model.data"]
        try:
            if self.env.context.get("send_rfq", False):
                template_id = ir_model_data._xmlid_lookup(
                    "purchase.email_template_edi_purchase",
                )[1]
            else:
                template_id = ir_model_data._xmlid_lookup(
                    "purchase.email_template_edi_purchase_done",
                )[1]
        except ValueError:
            template_id = False
        return template_id

    @api.model
    def _get_orders_to_remind(self):
        """When auto sending a reminder mail, only send for unconfirmed purchase
        order and not all products are service."""
        return self.search(
            [
                ("partner_id", "!=", False),
                ("state", "=", "done"),
                ("acknowledged", "=", False),
                ("receipt_reminder_email", "=", True),
            ],
        ).filtered(
            lambda p: p.mapped("line_ids.product_id.product_tmpl_id.type")
            != ["service"],
        )

    def _get_product_price_and_data(self, product):
        """Fetch the product's data used by the purchase's catalog.

        :return: the product's price and, if applicable, the minimum quantity to
                 buy and the product's packaging data.
        :rtype: dict
        """
        self.ensure_one()
        product_infos = {
            "price": product.standard_price,
            "uomDisplayName": product.uom_id.display_name,
        }
        params = {"order_id": self}
        # Check if there is a price and a minimum quantity for the order's vendor.
        seller = product._select_seller(
            partner_id=self.partner_id,
            quantity=None,
            date=self.date_order and self.date_order.date(),
            uom_id=product.uom_id,
            ordered_by="min_qty",
            params=params,
        )
        if seller:
            product_uom = (seller.product_id or seller.product_tmpl_id).uom_id
            price = seller.price_discounted
            if seller.currency_id != self.currency_id:
                price = seller.currency_id._convert(price, self.currency_id)
            if seller.product_uom_id != product_uom:
                # The discounted price is expressed in the product's UoM, not in the vendor
                # price's UoM, so we need to convert it into to match the displayed UoM.
                price = product_uom._compute_price(price, seller.product_uom_id)
                product_infos.update(
                    uomFactor=seller.product_uom_id.factor / product_uom.factor
                )
            product_infos.update(
                price=price,
                min_qty=seller.min_qty,
                uomDisplayName=seller.product_uom_id.display_name,
            )

        return product_infos

    def _get_report_base_filename(self):
        self.ensure_one()
        return f"Purchase Order-{self.name}"

    def get_timezone(self):
        """Returns the timezone of the order's user or the company's partner
        or UTC if none of them are set."""
        self.ensure_one()
        return timezone(self.user_id.tz or self.company_id.partner_id.tz or "UTC")

    def get_update_url(self):
        """Create portal url for user to update the scheduled date on purchase
        order lines."""
        update_param = url_encode({"update": "True"})
        return self.get_portal_url(query_string="&%s" % update_param)

    def _merge_alternative_po(self, rfqs):
        pass

    @api.model
    def prepare_dashboard(self):
        """This function returns the values to populate the custom dashboard in
        the purchase order views.
        """
        if not self.env.user._is_internal():
            raise AccessDenied()

        self.browse().check_access("read")

        result = {
            "global": {
                "draft": {"all": 0, "priority": 0},
                "sent": {"all": 0, "priority": 0},
                "late": {"all": 0, "priority": 0},
                "not_acknowledged": {"all": 0, "priority": 0},
                "late_receipt": {"all": 0, "priority": 0},
                "days_to_order": 0,
            },
            "my": {
                "draft": {"all": 0, "priority": 0},
                "sent": {"all": 0, "priority": 0},
                "late": {"all": 0, "priority": 0},
                "not_acknowledged": {"all": 0, "priority": 0},
                "late_receipt": {"all": 0, "priority": 0},
                "days_to_order": 0,
            },
            "days_to_purchase": 0,
        }

        def _update(key, dict_to_update, group):
            for priority, user_id, count in group:
                my = user_id == self.env.user
                dict_to_update["global"][key]["all"] += count
                if priority != "0":
                    dict_to_update["global"][key]["priority"] += count
                if not my:
                    continue
                dict_to_update["my"][key]["all"] += count
                if priority != "0":
                    dict_to_update["my"][key]["priority"] += count

        # easy counts
        groupby = ["priority", "user_id"]
        aggregate = ["id:count_distinct"]
        rfq_draft_domain = [("state", "=", "draft")]
        rfq_draft_group = self.env["purchase.order"]._read_group(
            rfq_draft_domain,
            groupby,
            aggregate,
        )
        _update("draft", result, rfq_draft_group)

        rfq_sent_domain = [("sent", "=", True)]
        rfq_sent_group = self.env["purchase.order"]._read_group(
            rfq_sent_domain,
            groupby,
            aggregate,
        )
        _update("sent", result, rfq_sent_group)

        rfq_late_domain = [
            ("state", "=", "draft"),
            ("date_order", "<", fields.Datetime.now()),
        ]
        rfq_late_group = self.env["purchase.order"]._read_group(
            rfq_late_domain,
            groupby,
            aggregate,
        )
        _update("late", result, rfq_late_group)

        rfq_not_acknowledge = [("state", "=", "done"), ("acknowledged", "=", False)]
        rfq_not_acknowledge_group = self.env["purchase.order"]._read_group(
            rfq_not_acknowledge,
            groupby,
            aggregate,
        )
        _update("not_acknowledged", result, rfq_not_acknowledge_group)

        rfq_late_receipt = [("state", "=", "done"), ("is_late", "=", True)]
        rfq_late_receipt_group = self.env["purchase.order"]._read_group(
            rfq_late_receipt,
            groupby,
            aggregate,
        )
        _update("late_receipt", result, rfq_late_receipt_group)

        three_months_ago = fields.Datetime.to_string(
            fields.Datetime.now() - relativedelta(months=3),
        )

        purchases = self.env["purchase.order"].search_fetch(
            [
                ("state", "=", "done"),
                ("create_date", ">=", three_months_ago),
                ("date_confirmed", "!=", False),
            ],
            ["create_date", "date_confirmed", "user_id"],
        )

        global_deliveries_seconds = 0
        my_deliveries_seconds = 0
        my_deliveries_count = 0

        for po in purchases:
            delivery_seconds = (po.date_confirmed - po.create_date).total_seconds()
            global_deliveries_seconds += delivery_seconds
            if po.user_id == self.env.user:
                my_deliveries_seconds += delivery_seconds
                my_deliveries_count += 1

        avg_global_deliveries_seconds = (
            global_deliveries_seconds / len(purchases) if purchases else 0
        )
        avg_my_deliveries_seconds = (
            my_deliveries_seconds / my_deliveries_count if my_deliveries_count else 0
        )
        result["global"]["days_to_order"] = float_repr(
            avg_global_deliveries_seconds / 60 / 60 / 24,
            precision_digits=2,
        )
        result["my"]["days_to_order"] = float_repr(
            avg_my_deliveries_seconds / 60 / 60 / 24,
            precision_digits=2,
        )

        return result

    def _prepare_down_payment_section_vals(self):
        self.ensure_one()
        context = {"lang": self.partner_id.lang}
        res = {
            "order_id": self.id,
            "display_type": "line_section",
            "is_downpayment": True,
            "sequence": (self.line_ids[-1:].sequence or 9) + 1,
            "name": _("Down Payments"),
        }
        del context
        return res

    def _prepare_grouped_data(self, rfq):
        return (rfq.partner_id.id, rfq.currency_id.id, rfq.dest_address_id.id)

    def _prepare_invoice_vals(self):
        """Prepare the dict of values to create the new invoice for a purchase order."""
        self.ensure_one()
        move_type = self.env.context.get("default_move_type", "in_invoice")
        partner_invoice = self.env["res.partner"].browse(
            self.partner_id.address_get(["invoice"])["invoice"],
        )
        partner_bank_id = self.commercial_partner_id.bank_ids.filtered_domain(
            [("company_id", "in", (False, self.company_id.id))],
        )[:1]

        values = {
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "partner_id": partner_invoice.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "fiscal_position_id": (
                self.fiscal_position_id
                or self.fiscal_position_id._get_fiscal_position(partner_invoice)
            ).id,
            "partner_bank_id": partner_bank_id.id,
            "invoice_user_id": self.user_id.id,
            "move_type": move_type,
            "narration": self.notes,
            "invoice_origin": self.name,
            "invoice_line_ids": [],
        }

        if self.journal_id:
            values["journal_id"] = self.journal_id.id

        return values

    def _prepare_supplierinfo(self, partner, line, price, currency):
        # Prepare supplierinfo data when adding a product
        return {
            "partner_id": partner.id,
            "sequence": (
                max(line.product_id.seller_ids.mapped("sequence")) + 1
                if line.product_id.seller_ids
                else 1
            ),
            "min_qty": 1.0,
            "price": price,
            "currency_id": currency.id,
            "discount": line.discount,
            "delay": 0,
        }

    def _send_reminder_mail(self, send_single=False):
        if not self.env.user.has_group("purchase.group_send_reminder"):
            return

        template = self.env.ref(
            "purchase.email_template_edi_purchase_reminder",
            raise_if_not_found=False,
        )
        if template:
            orders = self if send_single else self._get_orders_to_remind()
            for order in orders:
                date = order.date_planned
                if date and (
                    send_single
                    or (
                        date - relativedelta(days=order.reminder_date_before_receipt)
                    ).date()
                    == fields.Date.today()
                ):
                    if send_single:
                        return order._send_reminder_open_composer(template.id)
                    else:
                        order.with_context(is_reminder=True).message_post_with_source(
                            template,
                            email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                            subtype_xmlid="mail.mt_comment",
                        )

    def _send_reminder_open_composer(self, template_id):
        self.ensure_one()
        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "default_model": "purchase.order",
                "default_res_ids": self.ids,
                "default_template_id": template_id,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                "force_email": True,
                "mark_rfq_as_sent": True,
                "model_description": _(self.type_name),
            },
        )
        lang = self.env.context.get("lang")
        if {"default_template_id", "default_model", "default_res_id"} <= ctx.keys():
            template = self.env["mail.template"].browse(template_id)
            if template and template.lang:
                lang = template._render_lang([ctx["default_res_id"]])[
                    ctx["default_res_id"]
                ]
        self = self.with_context(lang=lang)
        compose_form_id = self._get_mail_compose_form()
        return {
            "name": _("Compose Email"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def send_reminder_preview(self):
        self.ensure_one()
        if not self.env.user.has_group("purchase.group_send_reminder"):
            return

        template = self.env.ref(
            "purchase.email_template_edi_purchase_reminder",
            raise_if_not_found=False,
        )
        if template and self.env.user.email and self.id:
            template.with_context(is_reminder=True).send_mail(
                self.id,
                force_send=True,
                raise_exception=False,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                email_values={"email_to": self.env.user.email, "recipient_ids": []},
            )
            return {
                "toast_message": escape(
                    _("A sample email has been sent to %s.", self.env.user.email),
                ),
            }

    def _update_order_lines_date_planned(self, updated_dates):
        # create or update the activity
        activity = self.env["mail.activity"].search(
            [
                ("summary", "=", _("Date Updated")),
                ("res_model_id", "=", "purchase.order"),
                ("res_id", "=", self.id),
                ("user_id", "=", self.user_id.id),
            ],
            limit=1,
        )
        if activity:
            self._update_update_date_activity(updated_dates, activity)
        else:
            self._create_update_date_activity(updated_dates)

        # update the date on PO line
        for line, date in updated_dates:
            line._update_date_planned(date)

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _can_confirm(self):
        """Validate that purchase orders can be confirmed.

        Validates in order:
        1. Orders are in correct state (draft or sent)
        2. Orders have at least one line
        3. All lines have products assigned
        4. (Extensible) Custom validations from other modules

        This method is designed to be extensible in two ways:

        Method 1 - Override this method (simple):
            class PurchaseOrder(models.Model):
                _inherit = 'purchase.order'

                def _can_confirm(self):
                    super()._can_confirm()
                    self._can_confirm_budget_available()  # Custom validation

        Method 2 - Use validation registry (recommended for complex scenarios):
            class PurchaseOrder(models.Model):
                _inherit = 'purchase.order'

                def _get_can_confirm_validation_methods(self):
                    methods = super()._get_can_confirm_validation_methods()
                    methods.append('_can_confirm_budget_available')
                    return methods

        :raises UserError: If any validation fails
        """
        # Execute all registered validation methods dynamically
        for method_name in self._get_can_confirm_validation_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)()
            # Note: If method doesn't exist, skip silently to allow gradual adoption

    def _get_can_confirm_validation_methods(self):
        """Return list of validation method names to be called by _can_confirm.

        This method can be overridden by other modules to add custom validation
        methods without modifying the core _can_confirm method. This is useful
        for modules that need to add domain-specific confirmation restrictions.

        Example usage in custom budget module:

        class PurchaseOrder(models.Model):
            _inherit = 'purchase.order'

            def _get_can_confirm_validation_methods(self):
                methods = super()._get_can_confirm_validation_methods()
                methods.append('_can_confirm_budget_available')
                return methods

            def _can_confirm_budget_available(self):
                orders_over_budget = self.filtered(
                    lambda o: o.amount_total > o.department_id.available_budget
                )
                if orders_over_budget:
                    raise UserError(
                        _("Cannot confirm orders exceeding available budget: %s",
                          format_list(self.env, orders_over_budget.mapped("display_name")))
                    )

        :return: List of validation method names to call
        :rtype: list[str]
        """
        return [
            "_can_confirm_proper_state",
            "_can_confirm_has_lines",
            "_can_confirm_lines_have_product",
            "_can_confirm_analytic_distribution",
        ]

    def _can_confirm_has_lines(self):
        """Ensure orders have at least one order line.

        Purchase orders must have at least one line item to be confirmed.
        Empty orders cannot be processed.
        """
        orders_without_lines = self.filtered(lambda order: not order.line_ids)
        if orders_without_lines:
            raise UserError(
                _(
                    "Cannot confirm purchase orders without lines: %s\n\n"
                    "Please add at least one product line before confirming.",
                    format_list(self.env, orders_without_lines.mapped("display_name")),
                ),
            )

    def _can_confirm_lines_have_product(self):
        """Ensure all non-display lines have products assigned.

        All product lines (excluding section/note lines and down payments) must
        have a product selected before the order can be confirmed.
        """
        orders_without_line_product = self.filtered(
            lambda order: any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in order.line_ids
            ),
        )
        if orders_without_line_product:
            # Build detailed error showing which orders have the issue
            error_details = []
            for order in orders_without_line_product:
                missing_product_lines = order.line_ids.filtered(
                    lambda l: not l.display_type
                    and not l.is_downpayment
                    and not l.product_id,
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
                    "Cannot confirm purchase orders with lines missing products:\n\n%s\n\n"
                    "Please assign a product to all order lines before confirming.",
                    "\n".join(error_details),
                ),
            )

    def _can_confirm_proper_state(self):
        """Ensure orders are in draft state (RFQ).

        Only orders in RFQ (draft) state can be confirmed. Orders already
        confirmed (purchase state) or cancelled cannot be confirmed.
        """
        orders_wrong_state = self.filtered(lambda order: order.state != "draft")
        if orders_wrong_state:
            # Categorize by state for better error message
            purchase_orders = orders_wrong_state.filtered(
                lambda o: o.state == "done",
            )
            cancelled_orders = orders_wrong_state.filtered(
                lambda o: o.state == "cancel",
            )

            error_parts = []
            if purchase_orders:
                error_parts.append(
                    _(
                        "• Already confirmed: %s",
                        format_list(self.env, purchase_orders.mapped("display_name")),
                    ),
                )
            if cancelled_orders:
                error_parts.append(
                    _(
                        "• Cancelled: %s",
                        format_list(self.env, cancelled_orders.mapped("display_name")),
                    ),
                )

            raise UserError(
                _(
                    "Cannot confirm purchase orders that are not in RFQ (draft) state:\n\n%s\n\n"
                    "Only orders in 'RFQ' state can be confirmed.",
                    "\n".join(error_parts),
                ),
            )

    def _can_confirm_analytic_distribution(self):
        """Ensure all order lines have valid analytic distributions.

        Analytic distributions must be validated before confirming the order
        to prevent creating confirmed orders with invalid accounting data.
        This validation is triggered when context key 'validate_analytic' is True.

        For each order with invalid analytics, collects the line numbers and
        specific validation errors to help users fix the issues.
        """
        if not self.env.context.get("validate_analytic"):
            return

        orders_with_errors = {}

        for order in self:
            line_errors = []
            for line in order.line_ids:
                if line.display_type:
                    continue
                try:
                    line._validate_distribution(
                        product=line.product_id.id,
                        business_domain="purchase_order",
                        company_id=line.company_id.id,
                    )
                except (UserError, ValidationError) as e:
                    line_errors.append(
                        _(
                            "  • Line %(line_num)s (%(product)s): %(error)s",
                            line_num=line.sequence or "?",
                            product=line.product_id.display_name or _("No product"),
                            error=str(e).split("\n")[0],  # First line of error message
                        ),
                    )

            if line_errors:
                orders_with_errors[order] = line_errors

        if orders_with_errors:
            error_details = []
            for order, line_errors in orders_with_errors.items():
                error_details.append(
                    _(
                        "%(order)s:\n%(lines)s",
                        order=order.display_name,
                        lines="\n".join(line_errors),
                    ),
                )

            raise UserError(
                _(
                    "Cannot confirm purchase orders with invalid analytic distributions:\n\n%s\n\n"
                    "Please fix the analytic distribution on the highlighted lines.",
                    "\n\n".join(error_details),
                ),
            )

    def _can_cancel(self):
        """Validate that purchase orders can be cancelled.

        Validates in order:
        1. Orders are not in 'cancel' state already
        2. Orders are not locked
        3. Orders have no posted vendor bills
        4. (Extensible) Custom validations from other modules

        This method is designed to be extensible in two ways:

        Method 1 - Override this method (simple):
            class PurchaseOrder(models.Model):
                _inherit = 'purchase.order'

                def _can_cancel(self):
                    super()._can_cancel()
                    self._can_cancel_except_receipts()  # Custom validation

        Method 2 - Use validation registry (recommended for complex scenarios):
            class PurchaseOrder(models.Model):
                _inherit = 'purchase.order'

                def _get_can_cancel_validation_methods(self):
                    methods = super()._get_can_cancel_validation_methods()
                    methods.append('_can_cancel_except_receipts')
                    return methods

        :raises UserError: If any validation fails
        """
        # Execute all registered validation methods dynamically
        for method_name in self._get_can_cancel_validation_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)()
            # Note: If method doesn't exist, skip silently to allow gradual adoption

    def _get_can_cancel_validation_methods(self):
        """Return list of validation method names to be called by _can_cancel.

        This method can be overridden by other modules to add custom validation
        methods without modifying the core _can_cancel method. This is useful
        for modules that need to add domain-specific cancellation restrictions.

        Example usage in purchase_stock module:

        class PurchaseOrder(models.Model):
            _inherit = 'purchase.order'

            def _get_can_cancel_validation_methods(self):
                methods = super()._get_can_cancel_validation_methods()
                methods.append('_can_cancel_except_receipts')
                return methods

            def _can_cancel_except_receipts(self):
                orders_with_receipts = self.filtered(
                    lambda o: o.picking_ids.filtered(lambda p: p.state == 'done')
                )
                if orders_with_receipts:
                    raise UserError(_("Cannot cancel orders with completed receipts"))

        :return: List of validation method names to call
        :rtype: list[str]
        """
        return [
            "_can_cancel_check_state",
            "_can_cancel_except_locked",
            "_can_cancel_except_invoiced",
        ]

    def _can_cancel_check_state(self):
        """Ensure orders are not already cancelled."""
        cancelled_orders = self.filtered(lambda order: order.state == "cancel")
        if cancelled_orders:
            raise UserError(
                _(
                    "The following purchase orders are already cancelled: %s",
                    format_list(self.env, cancelled_orders.mapped("display_name")),
                ),
            )

    def _can_cancel_except_locked(self):
        """Ensure orders are not locked.

        Locked orders require explicit unlocking before cancellation to prevent
        accidental modifications to confirmed purchase orders.
        """
        orders_locked = self.filtered(lambda order: order.locked)
        if orders_locked:
            raise UserError(
                _(
                    "Cannot cancel locked purchase orders: %s. "
                    "Please unlock them first using the 'Unlock' button.",
                    format_list(self.env, orders_locked.mapped("display_name")),
                ),
            )

    def _can_cancel_except_invoiced(self):
        """Ensure orders don't have posted vendor bills.

        Purchase orders with posted bills cannot be cancelled as this would
        create accounting inconsistencies. Bills must be cancelled first.

        Performance note: Uses filtered() to avoid loading all invoice records.
        """
        # Optimized: Use filtered instead of any() to leverage ORM
        orders_with_posted_invoices = self.filtered(
            lambda order: order.invoice_ids.filtered(lambda inv: inv.state == "posted"),
        )

        if orders_with_posted_invoices:
            # Build detailed error message with order and invoice info
            error_details = []
            for order in orders_with_posted_invoices:
                posted_bills = order.invoice_ids.filtered(lambda i: i.state == "posted")
                bill_names = ", ".join(posted_bills.mapped("name"))
                error_details.append(
                    _(
                        "• %(order)s has posted bills: %(bills)s",
                        order=order.display_name,
                        bills=bill_names,
                    ),
                )

            raise UserError(
                _(
                    "Cannot cancel purchase orders with posted vendor bills:\n\n%s\n\n"
                    "Please cancel or reset the bills to draft first.",
                    "\n".join(error_details),
                ),
            )

    def _must_delete_date_planned(self, field_name):
        # To be overridden
        return field_name == "line_ids"

    def _should_be_locked(self):
        """Check if sale order should be automatically locked on confirmation.

        Returns True if company configuration is set to lock confirmed orders.
        """
        self.ensure_one()
        return self.company_id.order_lock_po == "lock" or self.env.user.has_group(
            "purchase.group_auto_done_setting",
        )
