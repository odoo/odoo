from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UniversityBookRequirement(models.Model):
    _name = "university.book.requirement"
    _description = "Class Section Book Procurement Requirement"
    _order = "section_id, subject_id, id"
    _rec_name = "display_name"

    section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        required=True,
        ondelete="cascade",
        index=True,
    )
    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        required=True,
        ondelete="restrict",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Book Product",
        required=True,
        ondelete="restrict",
        domain="[('purchase_ok', '=', True)]",
        index=True,
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain="[('supplier_rank', '>', 0)]",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        check_company=True,
    )
    student_count = fields.Integer(string="Enrolled Students", readonly=True)
    students_with_books = fields.Integer(string="Students With Books", readonly=True)
    students_needing_books = fields.Integer(string="Students Needing Books", readonly=True)
    required_qty = fields.Float(string="Required Quantity", digits="Product Unit", readonly=True)
    available_qty = fields.Float(
        string="Available Quantity",
        digits="Product Unit",
        readonly=True,
        help="Free-to-use quantity in the company warehouse (on hand minus reserved).",
    )
    purchase_qty = fields.Float(string="Purchase Quantity", digits="Product Unit", readonly=True)
    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase Order Line",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    purchase_order_id = fields.Many2one(
        related="purchase_line_id.order_id",
        string="Purchase Order",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("rfq", "RFQ Created"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
        copy=False,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _section_subject_uniq = models.Constraint(
        "UNIQUE(section_id, subject_id)",
        "Only one book requirement is allowed per section and subject.",
    )

    @api.depends("section_id", "subject_id", "product_id")
    def _compute_display_name(self):
        for rec in self:
            parts = [
                rec.section_id.display_name or "",
                rec.subject_id.display_name or "",
                rec.product_id.display_name or "",
            ]
            rec.display_name = " / ".join(p for p in parts if p)

    @api.constrains("purchase_qty", "required_qty", "available_qty")
    def _check_quantities(self):
        for rec in self:
            if rec.required_qty < 0 or rec.available_qty < 0 or rec.purchase_qty < 0:
                raise ValidationError(_("Book requirement quantities cannot be negative."))

    def _purchase_order_is_mutable_rfq(self):
        """Draft/sent RFQs may be updated or cancelled; confirmed POs must not be altered."""
        self.ensure_one()
        order = self.purchase_order_id
        return bool(order) and order.state in ("draft", "sent", "cancel")

    def _unlink_mutable_purchase_line(self):
        """Remove the linked PO line when the RFQ is still mutable; cleanup empty draft POs."""
        self.ensure_one()
        line = self.purchase_line_id
        if not line:
            return
        order = line.order_id
        if order.state not in ("draft", "sent", "cancel"):
            raise UserError(
                _("Cannot modify purchase line on confirmed order %s.") % order.display_name
            )
        order_ref = order
        line.unlink()
        if order_ref.exists() and order_ref.state == "draft" and not order_ref.order_line:
            order_ref.unlink()

    def action_cancel(self):
        for rec in self:
            if rec.state == "rfq" and rec.purchase_order_id and not rec._purchase_order_is_mutable_rfq():
                raise UserError(
                    _(
                        "Cannot cancel requirement %(req)s because purchase order %(po)s is no longer a draft RFQ."
                    )
                    % {"req": rec.display_name, "po": rec.purchase_order_id.display_name}
                )
            if rec.purchase_line_id:
                rec._unlink_mutable_purchase_line()
            rec.write({
                "state": "cancel",
                "purchase_line_id": False,
            })
        return True

    def action_reset_draft(self):
        for rec in self:
            if rec.state == "rfq" and rec.purchase_order_id and not rec._purchase_order_is_mutable_rfq():
                raise UserError(
                    _("Cannot reset requirement linked to confirmed purchase order %s.")
                    % rec.purchase_order_id.display_name
                )
            if rec.purchase_line_id:
                rec._unlink_mutable_purchase_line()
            rec.write({"state": "draft", "purchase_line_id": False})
        return True
