from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError


class TourBooking(models.Model):
    _name = "tour.booking"
    _description = "Tour Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "booking_date desc, id desc"

    name = fields.Char(default="New", copy=False, readonly=True)
    customer_id = fields.Many2one("tour.customer", required=True, tracking=True)
    package_id = fields.Many2one("tour.package", required=True, tracking=True)
    booking_date = fields.Date(default=fields.Date.context_today, required=True)
    tour_date = fields.Date()
    adult_count = fields.Integer(default=1, required=True)
    child_count = fields.Integer(default=0)
    total_people = fields.Integer(compute="_compute_total_people", store=True)
    customer_type = fields.Selection(
        selection=[
            ("individual", "Individual"),
            ("couple", "Couple"),
            ("family", "Family"),
            ("group", "Group"),
            ("corporate", "Corporate"),
        ],
        compute="_compute_customer_type",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("quoted", "Quoted"),
            ("confirmed", "Confirmed"),
            ("transport_assigned", "Transport Assigned"),
            ("paid", "Paid"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    base_amount = fields.Float(compute="_compute_amounts", store=True)
    discount_amount = fields.Float(compute="_compute_amounts", store=True)
    total_amount = fields.Float(compute="_compute_amounts", store=True)
    payment_status = fields.Selection(
        selection=[
            ("unpaid", "Unpaid"),
            ("partial", "Partial"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
        ],
        default="unpaid",
        required=True,
        tracking=True,
    )
    transport_assignment_ids = fields.One2many("tour.transport.assignment", "booking_id", string="Transport Assignments")
    payment_ids = fields.One2many("tour.payment", "booking_id", string="Payments")
    group_member_ids = fields.One2many("tour.group.member", "booking_id", string="Group Members")
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("tour.booking") or "New"
        return super().create(vals_list)

    @api.depends("adult_count", "child_count")
    def _compute_total_people(self):
        for booking in self:
            booking.total_people = booking.adult_count + booking.child_count

    @api.depends("total_people", "child_count")
    def _compute_customer_type(self):
        for booking in self:
            if booking.total_people >= 10:
                booking.customer_type = "group"
            elif booking.total_people == 1:
                booking.customer_type = "individual"
            elif booking.total_people == 2 and booking.child_count == 0:
                booking.customer_type = "couple"
            elif booking.child_count > 0:
                booking.customer_type = "family"
            else:
                booking.customer_type = "corporate"

    @api.depends("package_id.base_price", "total_people", "child_count")
    def _compute_amounts(self):
        discount_rules = self.env["tour.discount.rule"].search([("active", "=", True)])
        group_rules = discount_rules.filtered(lambda r: r.discount_type == "group")
        family_rules = discount_rules.filtered(lambda r: r.discount_type == "family_children")
        for booking in self:
            booking.base_amount = booking.package_id.base_price * booking.total_people
            discount = 0.0
            applicable_group_rules = group_rules.filtered(lambda r: booking.total_people >= r.min_people)
            if applicable_group_rules:
                best_rule = max(applicable_group_rules, key=lambda r: r.min_people)
                discount += booking.base_amount * best_rule.percentage / 100.0 + best_rule.fixed_amount
            if booking.child_count > 0 and family_rules:
                best_rule = family_rules[0]
                discount += booking.base_amount * best_rule.percentage / 100.0 + best_rule.fixed_amount
            booking.discount_amount = min(discount, booking.base_amount)
            booking.total_amount = booking.base_amount - booking.discount_amount

    @api.constrains("adult_count", "child_count", "package_id")
    def _check_capacity(self):
        for booking in self:
            if booking.package_id and booking.total_people > booking.package_id.max_capacity:
                raise ValidationError(
                    "Total tourists (%s) exceeds the package's maximum capacity (%s)."
                    % (booking.total_people, booking.package_id.max_capacity)
                )

    def action_submit(self):
        for booking in self:
            if booking.state != "draft":
                raise UserError("Only draft bookings can be submitted for a quote.")
            booking.state = "quoted"

    def action_confirm(self):
        for booking in self:
            if not booking.tour_date:
                raise UserError("A tour date is required to confirm the booking.")
            if booking.state not in ("draft", "quoted"):
                raise UserError("Only draft or quoted bookings can be confirmed.")
            booking.state = "confirmed"

    def action_assign_transport(self):
        for booking in self:
            if booking.state != "confirmed":
                raise UserError("Only confirmed bookings can have transport assigned.")
            if not booking.transport_assignment_ids:
                raise UserError("Add at least one transport assignment before continuing.")
            booking.state = "transport_assigned"

    def action_mark_paid(self):
        for booking in self:
            if booking.payment_status != "paid":
                raise UserError("Register full payment before marking the booking as paid.")
            booking.state = "paid"

    def action_complete(self):
        for booking in self:
            if booking.state != "paid":
                raise UserError("Only paid bookings can be completed.")
            booking.state = "completed"

    def action_cancel(self):
        for booking in self:
            if booking.state == "completed":
                raise UserError("Completed bookings cannot be cancelled.")
            booking.state = "cancelled"

    def _update_payment_status(self):
        for booking in self:
            if any(payment.state == "refunded" for payment in booking.payment_ids):
                booking.payment_status = "refunded"
                continue
            confirmed_amount = sum(booking.payment_ids.filtered(lambda p: p.state == "confirmed").mapped("amount"))
            if confirmed_amount <= 0:
                booking.payment_status = "unpaid"
            elif confirmed_amount >= booking.total_amount:
                booking.payment_status = "paid"
            else:
                booking.payment_status = "partial"
