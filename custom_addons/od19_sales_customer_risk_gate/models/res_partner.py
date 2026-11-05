from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_blacklist_status = fields.Selection(
        selection=[("normal", "Normal"), ("blacklisted", "Blacklisted")],
        string="Blacklist Status",
        default="normal",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
    )
    od19_blacklist_reason = fields.Text(
        string="Blacklist Reason",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_request_state = fields.Selection(
        selection=[
            ("not_requested", "Not Requested"),
            ("pending", "Pending Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Request State",
        default="not_requested",
        tracking=True,
        copy=False,
        groups="base.group_user",
    )
    od19_credit_limit_amount = fields.Monetary(
        string="Credit Limit Amount",
        currency_field="od19_credit_currency_id",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
        help="Maximum credit amount allowed for this customer.",
    )
    od19_credit_currency_id = fields.Many2one(
        "res.currency",
        string="Credit Currency",
        default=lambda self: self.env.company.currency_id,
        copy=False,
    )
    od19_credit_used_amount = fields.Monetary(
        string="Credit Used Amount",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_used_amount",
        store=False,
        copy=False,
        help="Sum of unpaid invoices and confirmed sale order amounts.",
    )
    od19_credit_available = fields.Monetary(
        string="Credit Available",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_available",
        store=False,
        copy=False,
        help="Credit limit minus credit used.",
    )
    od19_credit_expiry_date = fields.Date(
        string="Credit Expiry Date",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
        help="Date when the credit approval expires.",
    )
    od19_credit_sale_allowed = fields.Boolean(
        string="Credit Sale Allowed",
        compute="_compute_od19_credit_sale_allowed",
        store=True,
        copy=False,
        help="Customer is allowed to buy on credit terms.",
    )
    od19_credit_requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        tracking=True,
        copy=False,
        readonly=True,
    )
    od19_credit_request_date = fields.Datetime(
        string="Requested On",
        tracking=True,
        copy=False,
        readonly=True,
    )
    od19_credit_review_owner_id = fields.Many2one(
        "res.users",
        string="Review Owner",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_review_date = fields.Datetime(
        string="Reviewed On",
        tracking=True,
        copy=False,
        readonly=True,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_review_note = fields.Text(
        string="Review Note",
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_aging_hold_enabled = fields.Boolean(
        string="Apply Aging Hold",
        default=True,
        copy=False,
        tracking=True,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
        help="When enabled, this customer is placed on credit hold automatically "
        "once overdue receivables exceed the company tolerance.",
    )
    od19_credit_overdue_amount = fields.Monetary(
        string="Overdue Amount",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_aging",
        store=False,
        copy=False,
        help="Total outstanding amount of invoices past their due date.",
    )
    od19_credit_oldest_overdue_days = fields.Integer(
        string="Oldest Overdue (days)",
        compute="_compute_od19_credit_aging",
        store=False,
        copy=False,
        help="Number of days since the due date of the oldest unpaid invoice.",
    )
    od19_credit_rolling_limit = fields.Monetary(
        string="Rolling Credit Limit",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_aging",
        store=False,
        copy=False,
        help="Credit limit reduced by the overdue amount; the effective limit "
        "available for new credit sales.",
    )
    od19_credit_on_hold = fields.Boolean(
        string="On Credit Hold",
        compute="_compute_od19_credit_aging",
        store=False,
        copy=False,
        help="The customer is on credit hold because overdue receivables "
        "exceed the company tolerance.",
    )
    od19_credit_hold_reason = fields.Char(
        string="Credit Hold Reason",
        compute="_compute_od19_credit_aging",
        store=False,
        copy=False,
    )

    _OD19_PROTECTED_FIELDS = {
        "od19_blacklist_status",
        "od19_blacklist_reason",
        "od19_credit_request_state",
        "od19_credit_review_date",
        "od19_credit_limit_amount",
        "od19_credit_expiry_date",
        "od19_credit_aging_hold_enabled",
    }

    @api.depends(
        "od19_credit_request_state",
        "od19_credit_expiry_date",
        "od19_credit_limit_amount",
    )
    def _compute_od19_credit_sale_allowed(self):
        today = fields.Date.context_today(self)
        for partner in self:
            # Credit limit / expiry are restricted fields, but this stored
            # compute runs for every user that touches the partner.  Read them
            # with sudo() so the gate state stays accurate for all users.
            commercial = partner.commercial_partner_id.sudo()
            is_approved = commercial.od19_credit_request_state == "approved"
            not_expired = (
                not commercial.od19_credit_expiry_date
                or commercial.od19_credit_expiry_date >= today
            )
            # Compute available credit on the fly to avoid stale stored data
            used = commercial.od19_credit_used_amount
            available = commercial.od19_credit_limit_amount - used
            has_available_credit = (
                not commercial.od19_credit_limit_amount or available > 0
            )
            partner.od19_credit_sale_allowed = (
                is_approved and not_expired and has_available_credit
            )

    def _compute_od19_credit_used_amount(self):
        for partner in self:
            commercial = partner.commercial_partner_id
            # Unpaid customer invoices (posted, not fully reconciled)
            invoice_domain = [
                ("partner_id.commercial_partner_id", "=", commercial.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
            ]
            invoices = self.env["account.move"].sudo().search(invoice_domain)
            unpaid = sum(invoices.mapped("amount_residual_signed"))
            # Confirmed sale orders (not yet invoiced fully)
            so_domain = [
                ("partner_id.commercial_partner_id", "=", commercial.id),
                ("state", "=", "sale"),
            ]
            orders = self.env["sale.order"].sudo().search(so_domain)
            order_amount = sum(orders.mapped("amount_total"))
            partner.od19_credit_used_amount = max(unpaid + order_amount, 0.0)

    @api.depends(
        "od19_credit_limit_amount",
        "od19_credit_used_amount",
        "od19_credit_rolling_limit",
    )
    def _compute_od19_credit_available(self):
        for partner in self:
            # Credit limit is a restricted field; read it with sudo() so the
            # computed available credit is visible to every user that needs it.
            # The rolling limit shrinks the effective limit by the overdue
            # amount so that ageing debt reduces buying power.
            partner.od19_credit_available = (
                partner.sudo().od19_credit_rolling_limit
                - partner.od19_credit_used_amount
            )

    @api.depends(
        "od19_credit_limit_amount",
        "od19_credit_aging_hold_enabled",
        "od19_credit_request_state",
    )
    def _compute_od19_credit_aging(self):
        """Compute overdue exposure, rolling limit and automatic credit hold.

        Overdue amounts are read from posted, not-yet-paid customer invoices
        whose due date is in the past.  The rolling limit is the approved
        limit minus the overdue amount, and the customer goes on hold when the
        oldest overdue invoice or the overdue amount exceeds the tolerance
        configured on the company.
        """
        today = fields.Date.context_today(self)
        for partner in self:
            commercial = partner.commercial_partner_id.sudo()
            invoices = (
                self.env["account.move"]
                .sudo()
                .search(
                    [
                        ("partner_id.commercial_partner_id", "=", commercial.id),
                        ("move_type", "in", ("out_invoice", "out_refund")),
                        ("state", "=", "posted"),
                        ("payment_state", "not in", ("paid", "reversed")),
                    ]
                )
            )
            overdue_amount = 0.0
            oldest_overdue_days = 0
            for invoice in invoices:
                residual = invoice.amount_residual_signed
                if residual <= 0:
                    continue
                due_date = invoice.invoice_date_due or invoice.invoice_date
                if due_date and due_date < today:
                    overdue_amount += residual
                    oldest_overdue_days = max(
                        oldest_overdue_days, (today - due_date).days
                    )
            partner.od19_credit_overdue_amount = overdue_amount
            partner.od19_credit_oldest_overdue_days = oldest_overdue_days

            limit = commercial.od19_credit_limit_amount
            partner.od19_credit_rolling_limit = (
                max(limit - overdue_amount, 0.0) if overdue_amount else limit
            )

            company = partner.company_id.sudo() or self.env.company.sudo()
            reason = ""
            if (
                commercial.od19_credit_aging_hold_enabled
                and commercial.od19_credit_request_state == "approved"
                and company.od19_credit_hold_enabled
            ):
                max_days = company.od19_credit_hold_max_overdue_days or 0
                max_amount = company.od19_credit_hold_max_overdue_amount or 0.0
                if max_days and oldest_overdue_days > max_days:
                    reason = _(
                        "Overdue %(days)s days exceeds the %(limit)s-day tolerance."
                    ) % {"days": oldest_overdue_days, "limit": max_days}
                elif max_amount and overdue_amount > max_amount:
                    reason = _(
                        "Overdue amount %(amount).2f exceeds the %(limit).2f tolerance."
                    ) % {"amount": overdue_amount, "limit": max_amount}
            partner.od19_credit_on_hold = bool(reason)
            partner.od19_credit_hold_reason = reason

    def _od19_is_credit_reviewer(self):
        self.ensure_one()
        return self.env.user.has_group(
            "od19_sales_customer_risk_gate.group_od19_credit_reviewer"
        )

    def write(self, vals):
        if not self.env.su and not self._od19_is_credit_reviewer():
            if self._OD19_PROTECTED_FIELDS.intersection(vals):
                raise AccessError(
                    _("Only credit reviewers can modify customer risk fields.")
                )
        reval_fields = {"od19_blacklist_status", "od19_credit_request_state",
                        "od19_credit_expiry_date", "od19_credit_limit_amount",
                        "od19_credit_aging_hold_enabled"}
        needs_reval = bool(reval_fields.intersection(vals))
        res = super().write(vals)
        if needs_reval:
            self._od19_revalidate_open_documents()
        return res

    def _od19_revalidate_open_documents(self):
        """Revalidate open sale and purchase documents when risk fields change.

        When blacklist status, credit state, expiry date or credit limit
        changes, every open document of the commercial partner is re-checked.
        Documents that no longer pass the gate are blocked from further
        processing and a warning activity is scheduled so the responsible
        user can review them.
        """
        for partner in self:
            commercial = partner.commercial_partner_id
            sale_orders = self.env["sale.order"].sudo().search(
                [
                    ("partner_id.commercial_partner_id", "=", commercial.id),
                    ("state", "in", ("draft", "sent", "sale")),
                ]
            )
            for order in sale_orders:
                reason_code, message = order._od19_check_customer_gate(
                    "credit_revalidation"
                )
                if reason_code:
                    order._od19_log_gate_event(
                        commercial, reason_code, "credit_revalidation"
                    )
                    self._od19_notify_gate_block(order, commercial, message)
            purchase_orders = self.env["purchase.order"].sudo().search(
                [
                    ("partner_id.commercial_partner_id", "=", commercial.id),
                    ("state", "in", ("draft", "sent", "to approve")),
                ]
            )
            for order in purchase_orders:
                reason_code, message = order._od19_check_partner_gate(
                    "credit_revalidation"
                )
                if reason_code:
                    order._od19_log_gate_event(
                        commercial, reason_code, "credit_revalidation"
                    )
                    self._od19_notify_gate_block(order, commercial, message)

    def _od19_notify_gate_block(self, document, commercial, message):
        """Schedule a review activity on a document blocked by the risk gate."""
        owner = (
            commercial.sudo().od19_credit_review_owner_id
            or document.user_id
            or self.env.user
        )
        document.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=owner.id,
            summary=_("Risk gate: review required"),
            note=message,
        )

    def action_od19_request_credit(self):
        for partner in self:
            commercial = partner.commercial_partner_id
            if commercial.od19_credit_request_state in ("pending", "approved"):
                continue
            commercial.sudo().write(
                {
                    "od19_credit_request_state": "pending",
                    "od19_credit_requested_by": self.env.user.id,
                    "od19_credit_request_date": fields.Datetime.now(),
                }
            )
            owner = commercial.sudo().od19_credit_review_owner_id
            if owner:
                commercial.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=owner.id,
                    summary=_("Review credit request"),
                    note=_("Customer %s requested credit approval.")
                    % commercial.display_name,
                )
        return True

    def action_od19_approve_credit(self):
        self._od19_review_credit("approved")

    def action_od19_reject_credit(self):
        self._od19_review_credit("rejected")

    def _od19_review_credit(self, new_state):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can approve or reject credit requests.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            if commercial.od19_credit_request_state != "pending":
                raise UserError(
                    _("Credit request must be in 'Pending Review' state.")
                )
            if not commercial.od19_credit_review_note:
                raise UserError(
                    _("Please fill in the review note before deciding.")
                )
            commercial.sudo().write(
                {
                    "od19_credit_request_state": new_state,
                    "od19_credit_review_owner_id": self.env.user.id,
                    "od19_credit_review_date": fields.Datetime.now(),
                }
            )
            commercial.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Credit request %s.") % new_state,
            )
        return True

    def action_od19_set_blacklist(self):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can manage the blacklist.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            if not commercial.od19_blacklist_reason:
                raise UserError(
                    _("A blacklist reason is required before blacklisting.")
                )
            commercial.sudo().write({"od19_blacklist_status": "blacklisted"})
        return True

    def action_od19_clear_blacklist(self):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can manage the blacklist.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            commercial.sudo().write({"od19_blacklist_status": "normal"})
        return True

    def action_od19_recheck_credit_aging(self):
        """Refresh the ageing hold and revalidate the customer's open documents.

        Overdue receivables change without any write on the partner record
        (invoices get posted, paid or written off), so the automatic hold has
        to be refreshed on demand or by the nightly scheduler.  This action
        forces a re-check and revalidates every open document.
        """
        for partner in self:
            partner._od19_revalidate_open_documents()
            partner.message_post(body=_("Credit ageing re-checked."))
        return True

    @api.model
    def _cron_od19_recheck_credit_aging(self):
        """Nightly re-evaluation of the ageing hold for approved customers."""
        partners = self.sudo().search(
            [
                ("od19_credit_request_state", "=", "approved"),
                ("od19_credit_aging_hold_enabled", "=", True),
            ]
        )
        on_hold = partners.filtered(lambda p: p.od19_credit_on_hold)
        on_hold._od19_revalidate_open_documents()

    @api.model
    def od19_credit_gate_kpis(self):
        partners = self.env["res.partner"].search([])
        pending = partners.filtered(lambda p: p.od19_credit_request_state == "pending")
        rejected = partners.filtered(
            lambda p: p.od19_credit_request_state == "rejected"
        )
        events = self.env["od19.credit.gate.event"].search([])
        now = fields.Datetime.now()
        avg_age = 0.0
        if pending and any(p.od19_credit_request_date for p in pending):
            ages = [
                (now - p.od19_credit_request_date).total_seconds() / 86400.0
                for p in pending
                if p.od19_credit_request_date
            ]
            avg_age = sum(ages) / len(ages) if ages else 0.0
        return {
            "pending_count": len(pending),
            "pending_avg_age_days": avg_age,
            "rejected_count": len(rejected),
            "blocked_blacklist_count": len(
                events.filtered(lambda e: e.reason_code == "blacklist")
            ),
            "blocked_credit_count": len(
                events.filtered(
                    lambda e: e.reason_code in ("credit", "credit_hold")
                )
            ),
        }
