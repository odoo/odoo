"""
Base Order Mixin - Foundation for all order types (sale, purchase, etc.)

This mixin provides:
- Standardized field definitions
- State machine logic
- Workflow actions (confirm, cancel, lock/unlock)
- Extensible validation framework
- Common compute methods

Designed for Odoo 19+ with no backward compatibility constraints.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OrderMixin(models.AbstractModel):
    """Base mixin for all order types (sales, purchase, manufacturing, rental, etc.)

    This mixin consolidates common order management patterns that were previously
    duplicated across sale.order, purchase.order, and other order models.

    Key Features:
    - Standardized field naming (is_locked, is_sent, quantity, etc.)
    - Extensible state machine with hook methods
    - Validation registry pattern for easy extension
    - Consistent workflow actions across all order types

    Usage:
        class SaleOrder(models.Model):
            _name = 'sale.order'
            _inherit = ['order.mixin']

            # Implement abstract methods
            @api.model
            def _get_state_selection(self):
                return [
                    ('draft', 'Quotation'),
                    ('confirmed', 'Sales Order'),
                    ('done', 'Done'),
                    ('cancel', 'Cancelled'),
                ]
    """

    _name = "order.mixin"
    _description = "Order Management Base"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]

    # ============================================================
    # FIELDS - Standardized naming conventions
    # ============================================================

    # Core identification
    name = fields.Char(
        string="Reference",
        required=True,
        default=lambda self: _("New"),
        readonly=True,
        copy=False,
        index="trigram",
        help="Unique reference for this order",
    )

    # State - standardized across ALL order types
    state = fields.Selection(
        selection="_get_state_selection",
        string="Status",
        required=True,
        default="draft",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help="Current state of the order",
    )

    # Dates - consistent naming
    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        default=fields.Datetime.now,
        copy=False,
        index=True,
        tracking=True,
        help="Date when the order was created or confirmed",
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        readonly=True,
        copy=False,
        index=True,
        help="Date when the order was confirmed",
    )
    date_validity = fields.Date(
        string="Validity Date",
        copy=False,
        help="Order expires after this date (for quotations/RFQs)",
    )

    # Financial relationships
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
        ondelete="restrict",
    )
    currency_rate = fields.Float(
        string="Currency Rate",
        compute="_compute_currency_rate",
        store=True,
        digits=(12, 6),
        help="Exchange rate at order date",
    )

    # Partner relationship (override label in child models)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",  # Override: "Customer" or "Vendor"
        required=True,
        tracking=True,
        index=True,
        change_default=True,
        check_company=True,
    )

    # Responsible user (override label in child models)
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",  # Override: "Salesperson" or "Buyer"
        compute="_compute_user_id",
        store=True,
        readonly=False,
        tracking=True,
        index=True,
        domain="[('share', '=', False), ('company_ids', '=', company_id)]",
    )

    # Payment terms
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        compute="_compute_payment_term_id",
        store=True,
        readonly=False,
        check_company=True,
        domain="[('company_id', 'in', [False, company_id])]",
    )

    # Fiscal position
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        compute="_compute_fiscal_position_id",
        store=True,
        readonly=False,
        check_company=True,
        domain="[('company_id', 'in', [False, company_id])]",
        help="Fiscal positions are used to adapt taxes and accounts for particular partners",
    )

    # Control fields - renamed for clarity
    priority = fields.Selection(
        [("0", "Normal"), ("1", "High"), ("2", "Urgent")],
        string="Priority",
        default="0",
        index=True,
        tracking=True,
    )
    is_locked = fields.Boolean(
        string="Locked",
        default=False,
        copy=False,
        tracking=True,
        help="Locked orders cannot be modified",
    )

    # Communication tracking - renamed for clarity
    is_sent = fields.Boolean(
        string="Sent to Partner",
        default=False,
        copy=False,
        tracking=True,
        help="Whether the order has been sent to the partner",
    )
    send_count = fields.Integer(
        string="Times Sent",
        default=0,
        copy=False,
        help="Number of times this order was sent by email",
    )
    is_printed = fields.Boolean(
        string="Ever Printed",
        default=False,
        copy=False,
        tracking=True,
        help="Whether the order has been printed at least once",
    )
    print_count = fields.Integer(
        string="Times Printed",
        default=0,
        copy=False,
        help="Number of times this order was printed",
    )

    # References
    origin = fields.Char(
        string="Source Document",
        copy=False,
        index=True,
        help="Reference of the document that generated this order",
    )
    external_ref = fields.Char(
        string="External Reference",
        copy=False,
        help="Partner's reference for this order",
    )

    # Terms
    notes = fields.Html(
        string="Terms and Conditions",
        help="Default terms and conditions for this order type",
    )

    # ============================================================
    # COMPUTE METHODS
    # ============================================================

    @api.depends("currency_id", "company_id", "date_order")
    def _compute_currency_rate(self):
        """Compute currency rate at order date"""
        for order in self:
            order.currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(order.date_order or fields.Datetime.now()).date(),
            )

    @api.depends("company_id", "partner_id")
    def _compute_currency_id(self):
        """Compute currency from partner or company

        Override in child models to use partner-specific currency property:
        - Sale: partner_id.property_product_pricelist.currency_id
        - Purchase: partner_id.property_purchase_currency_id
        """
        for order in self:
            order.currency_id = order.company_id.currency_id

    @api.depends("partner_id")
    def _compute_user_id(self):
        """Compute responsible user from partner

        Override in child models to use partner-specific user property:
        - Sale: partner_id.user_id (salesperson)
        - Purchase: partner_id.user_purchase_id (buyer)
        """
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                # Recompute user on partner change
                # Only if order is new or has no user already
                order.user_id = (
                    self.env.user
                    if self.env.user.has_group("base.group_user")
                    else False
                )

    @api.depends("partner_id", "company_id")
    def _compute_payment_term_id(self):
        """Compute payment terms from partner

        Override in child models to use partner-specific property:
        - Sale: partner_id.property_payment_term_id
        - Purchase: partner_id.property_supplier_payment_term_id
        """
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = False

    @api.depends("partner_id", "company_id")
    def _compute_fiscal_position_id(self):
        """Compute fiscal position from partner"""
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

    # ============================================================
    # ABSTRACT METHODS - Must be implemented in child models
    # ============================================================

    @api.model
    def _get_state_selection(self):
        """Define state selection for this order type

        Example for sale:
            return [
                ('draft', 'Quotation'),
                ('sent', 'Quotation Sent'),
                ('confirmed', 'Sales Order'),
                ('done', 'Done'),
                ('cancel', 'Cancelled'),
            ]

        Example for purchase:
            return [
                ('draft', 'RFQ'),
                ('sent', 'RFQ Sent'),
                ('confirmed', 'Purchase Order'),
                ('done', 'Done'),
                ('cancel', 'Cancelled'),
            ]
        """
        raise NotImplementedError(f"{self._name} must implement _get_state_selection()")

    def _get_confirmed_state(self):
        """Return the 'confirmed' state name for this order type

        Usually 'confirmed', 'sale', or 'purchase'
        """
        return "confirmed"

    def _prepare_confirmation_values(self):
        """Prepare values for order confirmation

        Override to add model-specific fields

        Returns:
            dict: Values to write when confirming order
        """
        return {
            "state": self._get_confirmed_state(),
            "date_confirmed": fields.Datetime.now(),
        }

    def _get_order_type(self):
        """Return order type for settings and sequence codes

        Returns:
            str: 'sale', 'purchase', 'manufacturing', etc.
        """
        raise NotImplementedError(f"{self._name} must implement _get_order_type()")

    def _generate_sequence(self):
        """Generate sequence number for order

        Returns:
            str: Next sequence number
        """
        raise NotImplementedError(f"{self._name} must implement _generate_sequence()")

    # ============================================================
    # VALIDATION FRAMEWORK
    # ============================================================

    def _validate_confirmation(self):
        """Extensible validation before confirmation

        Runs all validation methods returned by _get_confirmation_validations()
        This allows child models to add validations without overriding this method.
        """
        for method_name in self._get_confirmation_validations():
            if hasattr(self, method_name):
                getattr(self, method_name)()

    def _get_confirmation_validations(self):
        """Return list of validation methods to run before confirmation

        Override and extend in child models:
            methods = super()._get_confirmation_validations()
            methods.extend(['_validate_my_custom_rule'])
            return methods

        Returns:
            list: Method names to call for validation
        """
        return [
            "_validate_has_lines",
            "_validate_proper_state",
        ]

    def _validate_has_lines(self):
        """Ensure order has at least one line"""
        orders_without_lines = self.filtered(lambda o: not o.line_ids)
        if orders_without_lines:
            raise UserError(
                _(
                    "Cannot confirm orders without lines:\n%s\n\n"
                    "Please add at least one product line before confirming.",
                    ", ".join(orders_without_lines.mapped("name")),
                )
            )

    def _validate_proper_state(self):
        """Ensure order is in draft state"""
        wrong_state = self.filtered(lambda o: o.state != "draft")
        if wrong_state:
            raise UserError(
                _(
                    "Only draft orders can be confirmed:\n%s\n\n"
                    "These orders are in wrong state.",
                    ", ".join(wrong_state.mapped("name")),
                )
            )

    def _validate_cancellation(self):
        """Validate order can be cancelled

        Runs basic checks plus custom validations from child models.
        """
        # Cannot cancel locked orders
        locked = self.filtered("is_locked")
        if locked:
            raise UserError(
                _(
                    "Cannot cancel locked orders:\n%s\n\n"
                    "Please unlock them first using the 'Unlock' button.",
                    ", ".join(locked.mapped("name")),
                )
            )

        # Additional validations from child models
        for method_name in self._get_cancellation_validations():
            if hasattr(self, method_name):
                getattr(self, method_name)()

    def _get_cancellation_validations(self):
        """Return list of validation methods for cancellation

        Override to add custom cancellation validations.

        Returns:
            list: Method names to call
        """
        return []

    # ============================================================
    # WORKFLOW ACTIONS
    # ============================================================

    def action_confirm(self):
        """Confirm order - extensible workflow

        This method:
        1. Validates the order can be confirmed
        2. Writes confirmation values
        3. Calls post-confirmation hook for model-specific logic
        4. Auto-locks if configured

        Returns:
            bool: True
        """
        self._validate_confirmation()
        self.write(self._prepare_confirmation_values())
        self._post_confirmation_hook()

        # Auto-lock if configured
        to_lock = self.filtered(lambda o: o._should_auto_lock())
        to_lock.action_lock()

        return True

    def _post_confirmation_hook(self):
        """Hook called after confirmation

        Override in child models to add model-specific logic:
        - Create delivery/receipt pickings
        - Update supplier/customer info
        - Send confirmation emails
        - etc.
        """
        pass

    def _should_auto_lock(self):
        """Check if order should auto-lock on confirmation

        Looks for company setting like 'auto_lock_sale', 'auto_lock_purchase', etc.

        Returns:
            bool: True if order should be locked
        """
        self.ensure_one()
        order_type = self._get_order_type()
        setting_field = f"auto_lock_{order_type}"
        return getattr(self.company_id, setting_field, False)

    def action_cancel(self):
        """Cancel order - extensible workflow

        This method:
        1. Validates the order can be cancelled
        2. Performs cancellation

        Returns:
            bool: True
        """
        self._validate_cancellation()
        return self._do_cancel()

    def _do_cancel(self):
        """Perform cancellation

        Override in child models to add logic:
        - Cancel related draft invoices
        - Cancel stock pickings
        - etc.

        Returns:
            bool: True
        """
        self.write({"state": "cancel"})
        return True

    def action_draft(self):
        """Set order back to draft

        Returns:
            bool: True
        """
        self.write({"state": "draft"})
        return True

    def action_lock(self):
        """Lock orders to prevent modifications

        Locked orders cannot be edited. Also resets priority to normal.

        Returns:
            bool: True
        """
        self.write({"is_locked": True, "priority": "0"})
        return True

    def action_unlock(self):
        """Unlock orders to allow modifications

        Returns:
            bool: True
        """
        self.write({"is_locked": False})
        return True

    # ============================================================
    # CRUD OVERRIDES
    # ============================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence number if needed"""
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._generate_sequence()
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Prevent deletion of confirmed orders"""
        confirmed = self.filtered(lambda o: o.state not in ("draft", "cancel"))
        if confirmed:
            raise UserError(
                _(
                    "Cannot delete confirmed orders. Cancel them first:\n%s",
                    ", ".join(confirmed.mapped("name")),
                )
            )

    # ============================================================
    # PORTAL/ACCESS
    # ============================================================

    def _compute_access_url(self):
        """Compute portal URL for order

        Override in child models to set proper portal route.
        """
        super()._compute_access_url()
        for order in self:
            # Child models should override this
            order.access_url = f"/my/orders/{order.id}"

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _get_report_base_filename(self):
        """Return filename for PDF reports

        Returns:
            str: Base filename for report
        """
        self.ensure_one()
        order_type = self._get_order_type().title()
        return f"{order_type} - {self.name}"
