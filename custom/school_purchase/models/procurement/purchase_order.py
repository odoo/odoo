"""School purchase order extensions: vendor metrics + class book purchasing."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


    on_time_rate_perc = fields.Float(
        string="On time rate",
        compute="_compute_on_time_rate_perc",
        store=True,
    )
    class_section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        index=True,
        copy=False,
        ondelete="set null",
        help="Class section that originated this book procurement RFQ.",
    )
    class_enrollment_ids = fields.One2many(
        related="class_section_id.enrollment_ids",
        string="Class Enrollments",
        readonly=True,
    )
    class_enrolled_count = fields.Integer(
        string="Enrolled Students",
        compute="_compute_class_validation_stats",
    )
    class_has_book_count = fields.Integer(
        string="Students With Books",
        compute="_compute_class_validation_stats",
    )
    class_no_book_count = fields.Integer(
        string="Students Needing Books",
        compute="_compute_class_validation_stats",
    )
    class_missing_book_config = fields.Boolean(
        string="Subjects Missing Book Config",
        compute="_compute_class_validation_stats",
    )
    class_validation_msg = fields.Char(
        string="Book Validation Status",
        compute="_compute_class_validation_stats",
    )

    @api.depends("on_time_rate")
    def _compute_on_time_rate_perc(self):
        for order in self:
            rate = order.on_time_rate
            order.on_time_rate_perc = rate / 100.0 if rate >= 0 else -1.0

    @api.depends(
        "class_section_id",
        "class_section_id.enrollment_ids",
        "class_section_id.enrollment_ids.status",
        "class_section_id.enrollment_ids.has_book",
        "class_section_id.enrollment_ids.subject_id",
        "class_section_id.enrollment_ids.subject_id.book_product_id",
        "class_section_id.subject_id",
        "class_section_id.subject_id.book_product_id",
    )
    def _compute_class_validation_stats(self):
        for order in self:
            if not order.class_section_id:
                order.class_enrolled_count = 0
                order.class_has_book_count = 0
                order.class_no_book_count = 0
                order.class_missing_book_config = False
                order.class_validation_msg = ""
                continue

            enrolled = order.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
            total_enrolled = len(enrolled)
            with_books = enrolled.filtered(lambda e: e.has_book)
            without_books = enrolled.filtered(lambda e: not e.has_book)
            missing_subs = order.class_section_id._subjects_missing_books()

            order.class_enrolled_count = total_enrolled
            order.class_has_book_count = len(with_books)
            order.class_no_book_count = len(without_books)
            order.class_missing_book_config = bool(missing_subs)

            if missing_subs:
                names = ", ".join(missing_subs.mapped("name"))
                order.class_validation_msg = _(
                    "[Missing Book Config] Subject(s) [%s] have enrolled students but no required books configured."
                ) % names
            elif total_enrolled == 0:
                order.class_validation_msg = _("No active enrolled students in this class section.")
            elif len(without_books) == 0:
                order.class_validation_msg = _(
                    "All %d enrolled student(s) already have books. No purchase required."
                ) % total_enrolled
            else:
                order.class_validation_msg = _(
                    "%d of %d student(s) need textbook purchase (%d already have books)."
                ) % (len(without_books), total_enrolled, len(with_books))

    @api.onchange("class_section_id")
    def _onchange_class_section_id(self):
        if self.class_section_id:
            if not self.partner_id and self.class_section_id.book_vendor_id:
                self.partner_id = self.class_section_id.book_vendor_id
            if not self.order_line:
                self._populate_class_book_lines()

    def _populate_class_book_lines(self):
        self.ensure_one()
        if not self.class_section_id:
            return
        enrolled = self.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        if not enrolled:
            return
        missing_subjects = self.class_section_id._subjects_missing_books()
        if missing_subjects:
            return

        students_needing_books = enrolled.filtered(lambda e: not e.has_book)
        if not students_needing_books:
            return

        subject_counts = {}
        for enrollment in students_needing_books:
            subject = enrollment.subject_id or self.class_section_id.subject_id
            if subject:
                subject_counts[subject] = subject_counts.get(subject, 0) + 1

        uom_field = (
            "product_uom_id"
            if "product_uom_id" in self.env["purchase.order.line"]._fields
            else "product_uom"
        )
        new_lines = []
        for subject, count in subject_counts.items():
            product = subject.book_product_id
            if not product or count <= 0:
                continue
            uom = getattr(product, "uom_po_id", False) or getattr(product, "uom_id", False)
            line_data = {
                "product_id": product.id,
                "name": _("%(subject)s — %(product)s (for %(count)s students needing book)")
                % {
                    "subject": subject.name,
                    "product": product.display_name,
                    "count": count,
                },
                "product_qty": count,
                "price_unit": product.standard_price,
                "date_planned": fields.Datetime.now(),
            }
            if uom:
                line_data[uom_field] = uom.id
            new_lines.append((0, 0, line_data))

        if new_lines:
            self.order_line = [(5, 0, 0)] + new_lines

    def action_populate_class_books(self):
        self.ensure_one()
        if not self.class_section_id:
            raise UserError(_("Please select a Class Section first."))

        enrolled = self.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        if not enrolled:
            raise UserError(
                _("No enrolled students found in class '%s'.") % self.class_section_id.display_name
            )

        missing_subjects = self.class_section_id._subjects_missing_books()
        if missing_subjects:
            subject_names = ", ".join(missing_subjects.mapped("name"))
            raise UserError(
                _(
                    "The following subjects have enrolled students but no required books configured: %s.\n"
                    "Please configure books on the subject first."
                )
                % subject_names
            )

        students_needing_books = enrolled.filtered(lambda e: not e.has_book)
        if not students_needing_books:
            raise UserError(
                _("All %d enrolled student(s) in this class already have their required books!")
                % len(enrolled)
            )

        self._populate_class_book_lines()
        if not self.partner_id and self.class_section_id.book_vendor_id:
            self.partner_id = self.class_section_id.book_vendor_id

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Book Lines Populated"),
                "message": _(
                    "Generated purchase order lines for %d student(s) needing books."
                )
                % len(students_needing_books),
                "type": "success",
                "sticky": False,
            },
        }

    def action_mark_all_students_has_book(self):
        self.ensure_one()
        if not self.class_section_id:
            raise UserError(_("Please select a Class Section first."))
        enrolled = self.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        enrolled.write({"has_book": True})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Student Book Status Updated"),
                "message": _("All %d enrolled student(s) marked as having book.") % len(enrolled),
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_all_students_no_book(self):
        self.ensure_one()
        if not self.class_section_id:
            raise UserError(_("Please select a Class Section first."))
        enrolled = self.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        enrolled.write({"has_book": False})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Student Book Status Updated"),
                "message": _("All %d enrolled student(s) reset to needing book.") % len(enrolled),
                "type": "info",
                "sticky": False,
            },
        }

    def action_mark_class_books_received(self):
        self.ensure_one()
        if not self.class_section_id:
            raise UserError(_("No Class Section associated with this purchase order."))
        enrolled = self.class_section_id.enrollment_ids.filtered(
            lambda e: e.status == "enrolled" and not e.has_book
        )
        enrolled.write({"has_book": True})
        # Mark linked requirements done when books are distributed.
        self.class_section_id.book_requirement_ids.filtered(
            lambda r: r.purchase_order_id == self and r.state in ("rfq", "ready")
        ).write({"state": "done"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Books Distributed"),
                "message": _("%d student(s) have been marked as having their books.") % len(enrolled),
                "type": "success",
                "sticky": False,
            },
        }
