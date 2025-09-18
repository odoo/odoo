"""
Base Order Mixin — Foundation for sale.order and purchase.order.

Provides the shared skeleton: fields, state machine, validation registry,
workflow actions, and compute methods that are identical (or near-identical)
across both order types.

``_get_order_type()`` is the primary routing key.  It returns ``'sale'`` or
``'purchase'`` and is used to derive sequence codes, group XML-IDs, company
settings, and display labels — so child models rarely need explicit overrides
for string-level differences.

Method and field names match the actual conventions in sale/purchase.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_list


class OrderMixin(models.AbstractModel):
    """Base mixin for sale.order and purchase.order.

    Consolidates patterns that were duplicated across both modules.
    Child models implement ``_get_order_type()`` and override hooks
    for model-specific behaviour.

    Usage::

        class SaleOrder(models.Model):
            _name = 'sale.order'
            _inherit = ['order.mixin', ...]

            def _get_order_type(self):
                return 'sale'

            @api.model
            def _get_state_selection(self):
                return [
                    ('draft', 'Quotation'),
                    ('done', 'Sales Order'),
                    ('cancel', 'Cancelled'),
                ]
    """

    _name = "order.mixin"
    _description = "Order Management Base"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]

    # ------------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------------

    name = fields.Char(
        string="Reference",
        required=True,
        default=lambda self: _("New"),
        readonly=True,
        copy=False,
        index="trigram",
    )
    state = fields.Selection(
        selection="_get_state_selection",
        string="Status",
        required=True,
        default="draft",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )

    # Dates
    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        default=fields.Datetime.now,
        copy=False,
        index=True,
        tracking=True,
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        readonly=True,
        copy=False,
        index=True,
    )
    date_validity = fields.Date(
        string="Validity Date",
        copy=False,
    )

    # Company & financial
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        compute="_compute_currency_id",
        store=True,
        readonly=False,
        precompute=True,
        ondelete="restrict",
    )
    currency_rate = fields.Float(
        string="Currency Rate",
        compute="_compute_currency_rate",
        store=True,
        precompute=True,
        digits=0,
    )

    # Partner
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        tracking=True,
        index=True,
        change_default=True,
        check_company=True,
    )

    # Responsible user
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        compute="_compute_user_id",
        store=True,
        readonly=False,
        precompute=True,
        tracking=True,
        index=True,
        domain="[('share', '=', False), ('company_ids', '=', company_id)]",
    )

    # Payment & fiscal
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        compute="_compute_payment_term_id",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        domain="[('company_id', 'in', [False, company_id])]",
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        compute="_compute_fiscal_position_id",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        domain="[('company_id', 'in', [False, company_id])]",
    )

    # Control fields
    priority = fields.Selection(
        selection=[("0", "Normal"), ("1", "Urgent")],
        string="Priority",
        default="0",
        index=True,
    )
    locked = fields.Boolean(
        string="Locked",
        default=False,
        copy=False,
        tracking=True,
    )

    # Communication tracking
    sent = fields.Boolean(default=False, copy=False, tracking=True)
    count_sent = fields.Integer(default=0, copy=False)
    printed_before = fields.Boolean(default=False, copy=False, tracking=True)
    count_print = fields.Integer(default=0, copy=False)

    # References
    origin = fields.Char(
        string="Source Document",
        copy=False,
        index="trigram",
    )
    partner_ref = fields.Char(
        string="Partner Reference",
        copy=False,
    )

    # Terms
    notes = fields.Html(string="Terms and Conditions")

    # Journal
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        compute="_compute_journal_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
    )

    # Computed status helpers
    is_expired = fields.Boolean(
        string="Is Expired",
        compute="_compute_is_expired",
    )
    type_name = fields.Char(
        string="Type Name",
        compute="_compute_type_name",
    )

    # ------------------------------------------------------------------
    # ORDER TYPE — primary routing key
    # ------------------------------------------------------------------

    def _get_order_type(self):
        """Return order type identifier used as a routing key.

        Used to derive:
        - Sequence code: ``f'{type}.order'``
        - Group XML-IDs: ``f'{type}.group_auto_done_setting'``
        - Company settings: ``f'order_lock_{type}'`` (planned convention)
        - Display labels and report filenames

        Returns:
            str: ``'sale'`` or ``'purchase'``
        """
        raise NotImplementedError(f"{self._name} must implement _get_order_type()")

    @api.model
    def _get_state_selection(self):
        """Return state selection list for this order type.

        Both sale and purchase use three states::

            [('draft', '...'), ('done', '...'), ('cancel', 'Cancelled')]
        """
        raise NotImplementedError(f"{self._name} must implement _get_state_selection()")

    # ------------------------------------------------------------------
    # COMPUTE — identical in sale and purchase
    # ------------------------------------------------------------------

    @api.depends("company_id", "currency_id", "date_order")
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(order.date_order or fields.Datetime.now()).date(),
            )

    @api.depends("state", "date_validity")
    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = (
                order.state == "draft"
                and order.date_validity
                and order.date_validity < today
            )

    def _compute_journal_id(self):
        """Stub — child models override to select sale/purchase journal."""
        self.journal_id = False

    @api.depends("state")
    def _compute_type_name(self):
        for order in self:
            if order.state in ("draft", "cancel"):
                order.type_name = order._get_draft_type_name()
            else:
                order.type_name = order._get_confirmed_type_name()

    # ------------------------------------------------------------------
    # COMPUTE — shared skeleton, child overrides for specifics
    # ------------------------------------------------------------------

    @api.depends("company_id", "partner_id")
    def _compute_currency_id(self):
        """Default: company currency.

        Override in child models:
        - Sale: pricelist currency
        - Purchase: partner purchase currency property
        """
        for order in self:
            order.currency_id = order.company_id.currency_id

    @api.depends("partner_id")
    def _compute_user_id(self):
        """Assign responsible user on partner change.

        The guard logic is shared.  Override ``_get_default_user_from_partner``
        to return the right user (salesperson vs buyer).
        """
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                order.user_id = order._get_default_user_from_partner()

    @api.depends("company_id", "partner_id")
    def _compute_payment_term_id(self):
        """Default: False.  Child overrides to read partner property."""
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = False

    @api.depends("company_id", "partner_id")
    def _compute_fiscal_position_id(self):
        """Base implementation (purchase pattern — no shipping partner).

        Sale overrides to add ``partner_shipping_id`` to the cache key
        and pass it to ``_get_fiscal_position()``.
        """
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

    # ------------------------------------------------------------------
    # HOOKS — override in child models
    # ------------------------------------------------------------------

    def _get_draft_type_name(self):
        """Display name for draft/cancel state (e.g. 'Quotation', 'RFQ')."""
        return _("Quotation")

    def _get_confirmed_type_name(self):
        """Display name for confirmed state (e.g. 'Sales Order', 'Purchase Order')."""
        order_type = self._get_order_type()
        return _("%(type)s Order", type=order_type.title())

    def _get_default_user_from_partner(self):
        """Return the user to assign as responsible.

        Override in child models to read from partner properties::

            Sale:     partner.user_id or commercial_partner.user_id or env.user
            Purchase: partner.user_purchase_id or commercial_partner.user_purchase_id or env.user
        """
        self.ensure_one()
        return (
            self.env.user
            if self.env.user.has_group("base.group_user")
            else self.env["res.users"]
        )

    def _prepare_confirmation_values(self):
        """Values to write when confirming.

        Override to add model-specific date fields::

            Sale:     {"state": "done", "date_order": now()}
            Purchase: {"state": "done", "date_confirmed": now()}
        """
        return {"state": "done"}

    def _action_confirm(self):
        """Post-confirmation hook.  Override for model-specific logic.

        Sale leaves empty; purchase creates supplier records.
        """

    def _action_cancel(self):
        """Perform cancellation.  Override to cancel draft invoices/pickings."""
        self.write({"state": "cancel"})
        return True

    def _should_be_locked(self):
        """Check if order should auto-lock after confirmation.

        Uses ``_get_order_type()`` to derive the group XML-ID::

            f'{order_type}.group_auto_done_setting'

        Override if the company setting field doesn't follow the
        ``order_lock_{order_type}`` convention yet.
        """
        self.ensure_one()
        order_type = self._get_order_type()
        group_xmlid = f"{order_type}.group_auto_done_setting"
        # Company setting follows planned convention: order_lock_{type}
        lock_field = f"order_lock_{order_type}"
        company_locks = getattr(self.company_id, lock_field, False)
        return (company_locks == "lock") or self.env.user.has_group(group_xmlid)

    def _is_readonly(self):
        """Whether order should be treated as read-only in UI.

        Sale overrides to add ``or self.locked``.
        """
        self.ensure_one()
        return self.state == "cancel"

    # ------------------------------------------------------------------
    # VALIDATION REGISTRY — _can_confirm / _can_cancel
    # ------------------------------------------------------------------

    def _can_confirm(self):
        """Run all confirmation validations."""
        for method_name in self._get_can_confirm_validation_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)()

    def _get_can_confirm_validation_methods(self):
        """Return list of validation method names for confirmation.

        Extend via super() in child models or bridge modules::

            methods = super()._get_can_confirm_validation_methods()
            methods.append('_can_confirm_my_custom_rule')
            return methods
        """
        return [
            "_can_confirm_proper_state",
            "_can_confirm_has_lines",
            "_can_confirm_lines_have_product",
            "_can_confirm_analytic_distribution",
        ]

    def _can_confirm_proper_state(self):
        orders_wrong_state = self.filtered(lambda order: order.state != "draft")
        if not orders_wrong_state:
            return
        confirmed_orders = orders_wrong_state.filtered(lambda o: o.state == "done")
        cancelled_orders = orders_wrong_state.filtered(lambda o: o.state == "cancel")
        error_parts = []
        if confirmed_orders:
            error_parts.append(
                _(
                    "• Already confirmed: %s",
                    format_list(self.env, confirmed_orders.mapped("display_name")),
                )
            )
        if cancelled_orders:
            error_parts.append(
                _(
                    "• Cancelled: %s",
                    format_list(self.env, cancelled_orders.mapped("display_name")),
                )
            )
        raise UserError(
            _(
                "Cannot confirm %(desc)s that are not in draft state:\n\n%(details)s",
                desc=self._description,
                details="\n".join(error_parts),
            )
        )

    def _can_confirm_has_lines(self):
        orders_without_lines = self.filtered(lambda order: not order.line_ids)
        if orders_without_lines:
            raise UserError(
                _(
                    "Cannot confirm %(desc)s without lines: %(orders)s\n\n"
                    "Please add at least one product line before confirming.",
                    desc=self._description,
                    orders=format_list(
                        self.env, orders_without_lines.mapped("display_name")
                    ),
                )
            )

    def _can_confirm_lines_have_product(self):
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
                )
            )
        raise UserError(
            _(
                "Cannot confirm %(desc)s with lines missing products:\n\n%(details)s\n\n"
                "Please assign a product to all order lines before confirming.",
                desc=self._description,
                details="\n".join(error_details),
            )
        )

    def _can_confirm_analytic_distribution(self):
        """Validate analytic distributions.  Implementations differ — override entirely."""

    # Cancel validation

    def _can_cancel(self):
        """Run all cancellation validations."""
        for method_name in self._get_can_cancel_validation_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)()

    def _get_can_cancel_validation_methods(self):
        """Return list of validation method names for cancellation.

        Base returns the two validators shared by sale and purchase.
        Purchase extends via super() to add ``_can_cancel_except_invoiced``.
        """
        return [
            "_can_cancel_check_state",
            "_can_cancel_except_locked",
        ]

    def _can_cancel_check_state(self):
        cancelled_orders = self.filtered(lambda order: order.state == "cancel")
        if cancelled_orders:
            raise UserError(
                _(
                    "The following %(desc)s are already cancelled: %(orders)s",
                    desc=self._description,
                    orders=format_list(
                        self.env, cancelled_orders.mapped("display_name")
                    ),
                )
            )

    def _can_cancel_except_locked(self):
        orders_locked = self.filtered(lambda order: order.locked)
        if orders_locked:
            raise UserError(
                _(
                    "Cannot cancel locked %(desc)s: %(orders)s. "
                    "Please unlock them first using the 'Unlock' button.",
                    desc=self._description,
                    orders=format_list(self.env, orders_locked.mapped("display_name")),
                )
            )

    # ------------------------------------------------------------------
    # WORKFLOW ACTIONS
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Confirm orders: validate → write state → post-confirm hook → auto-lock."""
        self._can_confirm()
        self.write(self._prepare_confirmation_values())
        self._action_confirm()
        self.filtered(lambda o: o._should_be_locked()).action_lock()
        return True

    def action_cancel(self):
        """Cancel orders: validate → perform cancellation."""
        self._can_cancel()
        return self._action_cancel()

    def action_draft(self):
        self.write({"state": "draft"})
        return True

    def action_lock(self):
        """Lock orders.  Purchase overrides to also reset priority."""
        self.write({"locked": True})
        return True

    def action_unlock(self):
        self.write({"locked": False})
        return True

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence number using order type as routing key."""
        seq_code = f"{self._get_order_type()}.order"
        for vals in vals_list:
            company_id = vals.get(
                "company_id", self.default_get(["company_id"])["company_id"]
            )
            self_comp = self.with_company(company_id)
            if vals.get("name", _("New")) == _("New"):
                date_order = vals.get(
                    "date_order",
                    self_comp.default_get(["date_order"])["date_order"],
                )
                seq_date = fields.Datetime.context_timestamp(
                    self_comp, fields.Datetime.to_datetime(date_order)
                )
                vals["name"] = self_comp.env["ir.sequence"].next_by_code(
                    seq_code, sequence_date=seq_date
                )
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        """Prevent deletion of confirmed orders."""
        confirmed = self.filtered(lambda o: o.state not in ("draft", "cancel"))
        if confirmed:
            raise UserError(
                _(
                    "Cannot delete confirmed %(desc)s. Cancel them first:\n%(orders)s",
                    desc=self._description,
                    orders=", ".join(confirmed.mapped("name")),
                )
            )

    # ------------------------------------------------------------------
    # PORTAL
    # ------------------------------------------------------------------

    def _compute_access_url(self):
        super()._compute_access_url()
        order_type = self._get_order_type()
        for order in self:
            order.access_url = f"/my/{order_type}/{order.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return f"{self.type_name} - {self.name}"
