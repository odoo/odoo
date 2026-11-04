from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare


class UniversityClassSection(models.Model):
    _inherit = "university.class.section"

    enroll_deadline = fields.Date(
        string="Enrollment Deadline",
        required=True,
        default=fields.Date.context_today,
        help="Deadline date for student enrollments used to gate book purchasing. "
             "Enrollment closes the day after this date.",
    )
    book_vendor_id = fields.Many2one(
        "res.partner",
        string="Fallback Book Vendor",
        domain="[('user_ids', '=', False), '|', ('supplier_rank', '>', 0), ('is_company', '=', True)]",
        help="Used only when a required book product has no vendor configured.",
    )
    purchase_order_ids = fields.One2many(
        "purchase.order",
        "class_section_id",
        string="Book Purchases",
        groups="school_management.group_school_admin,purchase.group_purchase_user",
    )
    purchase_order_count = fields.Integer(
        string="Purchase Orders Count",
        compute="_compute_purchase_order_count",
    )
    book_requirement_ids = fields.One2many(
        "university.book.requirement",
        "section_id",
        string="Book Requirements",
        groups="school_management.group_school_admin,school_management.group_school_registrar,school_management.group_school_teacher,school_management.group_university_teacher,school_management.group_school_hod,school_management.group_school_dean,purchase.group_purchase_user",
    )
    book_requirement_count = fields.Integer(
        string="Requirements Count",
        compute="_compute_book_procurement_kpis",
    )
    enroll_closed = fields.Boolean(
        string="Enrollment Closed",
        compute="_compute_enroll_status",
        store=True,
    )
    student_count = fields.Integer(
        string="Student Count",
        compute="_compute_enroll_status",
        store=True,
    )
    missing_books = fields.Boolean(
        string="Missing Books",
        compute="_compute_enroll_status",
        store=True,
    )
    students_with_book_count = fields.Integer(
        string="Students With Books",
        compute="_compute_enroll_status",
        store=True,
    )
    students_no_book_count = fields.Integer(
        string="Students Needing Books",
        compute="_compute_enroll_status",
        store=True,
    )
    subjects_requiring_books_count = fields.Integer(
        string="Subjects Requiring Books",
        compute="_compute_book_procurement_kpis",
    )
    total_required_books = fields.Float(
        string="Total Required Books",
        compute="_compute_book_procurement_kpis",
        digits="Product Unit",
    )
    total_available_stock = fields.Float(
        string="Available Stock",
        compute="_compute_book_procurement_kpis",
        digits="Product Unit",
    )
    total_purchase_qty = fields.Float(
        string="Total Purchase Qty",
        compute="_compute_book_procurement_kpis",
        digits="Product Unit",
    )

    def _subjects_missing_books(self):
        self.ensure_one()
        enrolled = self.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        subjects = self.env["university.subject"]
        for e in enrolled:
            sub = e.subject_id or self.subject_id
            if sub:
                subjects |= sub
        if self.subject_id:
            subjects |= self.subject_id
        return subjects.filtered(lambda s: not s.book_product_id)

    @api.depends(
        "enroll_deadline",
        "enrollment_ids.status",
        "enrollment_ids.has_book",
        "enrollment_ids.subject_id",
        "enrollment_ids.subject_id.book_product_id",
        "subject_id",
        "subject_id.book_product_id",
    )
    def _compute_enroll_status(self):
        today = fields.Date.context_today(self)
        for section in self:
            section.enroll_closed = bool(section.enroll_deadline and section.enroll_deadline < today)
            enrolled = section.enrollment_ids.filtered(lambda e: e.status == "enrolled")
            section.student_count = len(enrolled)
            section.students_with_book_count = len(enrolled.filtered(lambda e: e.has_book))
            section.students_no_book_count = len(enrolled.filtered(lambda e: not e.has_book))
            section.missing_books = bool(section._subjects_missing_books())

    @api.depends("purchase_order_ids")
    def _compute_purchase_order_count(self):
        for section in self:
            section.purchase_order_count = len(section.sudo().purchase_order_ids)

    @api.depends(
        "book_requirement_ids",
        "book_requirement_ids.state",
        "book_requirement_ids.required_qty",
        "book_requirement_ids.available_qty",
        "book_requirement_ids.purchase_qty",
        "book_requirement_ids.subject_id",
    )
    def _compute_book_procurement_kpis(self):
        for section in self:
            reqs = section.sudo().book_requirement_ids.filtered(lambda r: r.state != "cancel")
            section.book_requirement_count = len(reqs)
            section.subjects_requiring_books_count = len(reqs.mapped("subject_id"))
            section.total_required_books = sum(reqs.mapped("required_qty"))
            section.total_available_stock = sum(reqs.mapped("available_qty"))
            section.total_purchase_qty = sum(reqs.mapped("purchase_qty"))

    def _get_book_procurement_warehouse(self):
        self.ensure_one()
        company = self.env.company
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)],
            limit=1,
            order="id",
        )
        return warehouse

    def _get_product_free_qty(self, product, warehouse):
        product = product.with_company(self.env.company)
        if warehouse:
            product = product.with_context(warehouse_id=warehouse.id)
        return product.free_qty if "free_qty" in product._fields else product.qty_available

    def _resolve_book_vendor(self, product):
        self.ensure_one()
        seller = product._select_seller(quantity=1.0)
        if seller and seller.partner_id:
            return seller.partner_id
        if self.book_vendor_id:
            return self.book_vendor_id
        return self.env["res.partner"]

    def _get_seller_price(self, product, vendor, qty):
        seller = product._select_seller(partner_id=vendor, quantity=qty or 1.0)
        if seller:
            return seller.price, seller.product_uom_id or product.uom_po_id or product.uom_id
        return product.standard_price, product.uom_po_id or product.uom_id

    def _collect_enrollment_book_needs(self):
        """Return dict subject -> {student_ids needing books, with_books, enrolled_count}."""
        self.ensure_one()
        enrolled = self.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        by_subject = defaultdict(lambda: {"students": set(), "with_books": set(), "enrolled": set()})
        for enrollment in enrolled:
            subject = enrollment.subject_id or self.subject_id
            if not subject:
                continue
            student_id = enrollment.student_id.id
            by_subject[subject]["enrolled"].add(student_id)
            if enrollment.has_book:
                by_subject[subject]["with_books"].add(student_id)
            else:
                by_subject[subject]["students"].add(student_id)
        return by_subject

    def _check_can_manage_book_procurement(self):
        user = self.env.user
        if user.has_group("base.group_system"):
            return
        if user.has_group("school_management.group_school_admin"):
            return
        if user.has_group("purchase.group_purchase_manager"):
            return
        if user.has_group("purchase.group_purchase_user"):
            return
        raise AccessError(_("Only school administrators or purchase users can manage book procurement."))

    def _prepare_requirement_vals(self, subject, data, warehouse):
        self.ensure_one()
        product = subject.book_product_id
        enrolled_count = len(data["enrolled"])
        with_books = len(data["with_books"])
        needing = len(data["students"])
        required_qty = float(needing)
        available_qty = self._get_product_free_qty(product, warehouse) if needing else 0.0
        usable_available = min(available_qty, required_qty)
        purchase_qty = max(0.0, required_qty - usable_available)
        vendor = self._resolve_book_vendor(product)
        return {
            "section_id": self.id,
            "subject_id": subject.id,
            "product_id": product.id,
            "vendor_id": vendor.id if vendor else False,
            "company_id": self.env.company.id,
            "warehouse_id": warehouse.id if warehouse else False,
            "student_count": enrolled_count,
            "students_with_books": with_books,
            "students_needing_books": needing,
            "required_qty": required_qty,
            "available_qty": usable_available,
            "purchase_qty": purchase_qty,
            "state": "ready",
            "purchase_line_id": False,
        }

    def _sync_mutable_rfq_requirement(self, req, vals):
        """Controlled update of a requirement still linked to a draft/sent RFQ."""
        self.ensure_one()
        order = req.purchase_order_id
        product_changed = vals["product_id"] != req.product_id.id
        vendor_changed = vals["vendor_id"] != (req.vendor_id.id if req.vendor_id else False)

        if product_changed or vendor_changed or not order or order.state == "cancel":
            if req.purchase_line_id:
                req._unlink_mutable_purchase_line()
            vals = dict(vals)
            vals["state"] = "ready"
            vals["purchase_line_id"] = False
            req.write(vals)
            return

        purchase_qty = vals["purchase_qty"]
        if float_compare(purchase_qty, 0.0, precision_digits=2) <= 0:
            if req.purchase_line_id:
                req._unlink_mutable_purchase_line()
            vals = dict(vals)
            vals["state"] = "ready"
            vals["purchase_line_id"] = False
            req.write(vals)
            return

        if req.purchase_line_id:
            line_vals = {"product_qty": purchase_qty}
            price, uom = self._get_seller_price(req.product_id, req.vendor_id, purchase_qty)
            line_vals["price_unit"] = price
            if "product_uom_id" in self.env["purchase.order.line"]._fields and uom:
                line_vals["product_uom_id"] = uom.id
            elif "product_uom" in self.env["purchase.order.line"]._fields and uom:
                line_vals["product_uom"] = uom.id
            req.purchase_line_id.write(line_vals)
            vals = dict(vals)
            vals["state"] = "rfq"
            vals["purchase_line_id"] = req.purchase_line_id.id
            req.write(vals)
        else:
            vals = dict(vals)
            vals["state"] = "ready"
            vals["purchase_line_id"] = False
            req.write(vals)

    def action_compute_book_requirements(self):
        self._check_can_manage_book_procurement()
        Requirement = self.env["university.book.requirement"]
        for section in self:
            if not section.enroll_closed:
                raise UserError(_("Enrollment is still open. Close enrollment before computing book requirements."))
            enrolled = section.enrollment_ids.filtered(lambda e: e.status == "enrolled")
            if not enrolled:
                raise UserError(_("No enrolled students found in this class section."))
            missing = section._subjects_missing_books()
            if missing:
                raise UserError(
                    _("Configure a required book on these subjects first: %s")
                    % ", ".join(missing.mapped("name"))
                )

            # Lock section + requirement rows to reduce concurrent double-compute races.
            self.env.cr.execute(
                "SELECT id FROM university_class_section WHERE id = %s FOR UPDATE",
                [section.id],
            )
            self.env.cr.execute(
                "SELECT id FROM university_book_requirement WHERE section_id = %s FOR UPDATE",
                [section.id],
            )
            section.invalidate_recordset(["book_requirement_ids"])

            blocked = section.book_requirement_ids.filtered(
                lambda r: r.state in ("rfq", "done")
                and r.purchase_order_id
                and r.purchase_order_id.state not in ("draft", "cancel", "sent")
            )
            if blocked:
                raise UserError(
                    _(
                        "Cannot recalculate: requirement(s) are linked to confirmed purchase orders "
                        "(%s). Cancel or complete those orders first, or reset draft RFQs."
                    )
                    % ", ".join(blocked.mapped("purchase_order_id").mapped("display_name"))
                )

            warehouse = section._get_book_procurement_warehouse()
            needs = section._collect_enrollment_book_needs()
            existing_by_subject = {
                req.subject_id: req
                for req in section.book_requirement_ids
            }
            processed_subjects = self.env["university.subject"]
            create_vals = []

            for subject, data in needs.items():
                product = subject.book_product_id
                if not product:
                    continue
                vals = section._prepare_requirement_vals(subject, data, warehouse)
                existing = existing_by_subject.get(subject)
                processed_subjects |= subject

                if existing and existing.state == "rfq" and existing._purchase_order_is_mutable_rfq():
                    section._sync_mutable_rfq_requirement(existing, vals)
                elif existing and existing.state in ("draft", "ready", "cancel"):
                    existing.write(vals)
                elif existing and existing.state == "rfq" and not existing.purchase_order_id:
                    existing.write(vals)
                elif not existing:
                    create_vals.append(vals)
                else:
                    # Unexpected state — reset via cancel path is safer than silent change.
                    raise UserError(
                        _("Cannot recalculate requirement %s in its current state.")
                        % existing.display_name
                    )

            # Subjects no longer needed: cancel mutable RFQs / remove draft rows.
            obsolete = section.book_requirement_ids.filtered(
                lambda r: r.subject_id not in processed_subjects
            )
            for req in obsolete:
                if req.state == "rfq" and req.purchase_order_id and not req._purchase_order_is_mutable_rfq():
                    raise UserError(
                        _("Cannot remove requirement linked to confirmed purchase order %s.")
                        % req.purchase_order_id.display_name
                    )
                if req.purchase_line_id:
                    req._unlink_mutable_purchase_line()
                if req.state in ("draft", "ready", "cancel"):
                    req.unlink()
                else:
                    req.write({"state": "cancel", "purchase_line_id": False})

            if create_vals:
                Requirement.create(create_vals)

            active = section.book_requirement_ids.filtered(lambda r: r.state != "cancel")
            if not active:
                raise UserError(_("No book requirements to compute for this section."))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Book Requirements Computed"),
                "message": _("Requirements were recalculated for the selected class section(s)."),
                "type": "success",
                "sticky": False,
            },
        }

    def _check_ready_for_book_purchase(self):
        self.ensure_one()
        if not self.enroll_closed:
            raise UserError(_("Enrollment deadline is not over yet."))
        enrolled = self.enrollment_ids.filtered(lambda e: e.status == "enrolled")
        if not enrolled:
            raise UserError(_("No enrolled students found in this class section."))
        missing = self._subjects_missing_books()
        if missing:
            raise UserError(
                _("The following subjects have enrolled students but no required books configured: %s")
                % ", ".join(missing.mapped("name"))
            )
        open_reqs = self.book_requirement_ids.filtered(lambda r: r.state in ("draft", "ready"))
        if not open_reqs:
            existing_rfq = self.book_requirement_ids.filtered(
                lambda r: r.state == "rfq"
                and r.purchase_order_id
                and r.purchase_order_id.state not in ("cancel",)
            )
            if existing_rfq:
                raise UserError(
                    _(
                        "Book purchase RFQs already exist for this section (%s). "
                        "Cancel the draft RFQ or reset requirements before creating another purchase."
                    )
                    % ", ".join(existing_rfq.mapped("purchase_order_id").mapped("display_name"))
                )
            raise UserError(
                _("No ready book requirements found. Click Compute Requirements first.")
            )
        purchasable = open_reqs.filtered(lambda r: float_compare(r.purchase_qty, 0.0, precision_digits=2) > 0)
        if not purchasable:
            raise UserError(_("All required books are covered by available stock. No purchase is needed."))
        missing_vendor = purchasable.filtered(lambda r: not r.vendor_id)
        if missing_vendor:
            raise UserError(
                _(
                    "Set a vendor on the book product (or a fallback Book Vendor on the section) for: %s"
                )
                % ", ".join(missing_vendor.mapped("product_id.display_name"))
            )

    def action_create_book_purchase(self):
        self._check_can_manage_book_procurement()
        created_orders = self.env["purchase.order"]
        for section in self:
            section.ensure_one()
            self.env.cr.execute(
                "SELECT id FROM university_class_section WHERE id = %s FOR UPDATE",
                [section.id],
            )
            self.env.cr.execute(
                "SELECT id FROM university_book_requirement WHERE section_id = %s FOR UPDATE",
                [section.id],
            )
            section.invalidate_recordset(["book_requirement_ids"])

            # Auto-compute if requirements missing or only cancelled/draft placeholders.
            active_reqs = section.book_requirement_ids.filtered(lambda r: r.state != "cancel")
            if not active_reqs or all(r.state == "draft" for r in active_reqs):
                section.action_compute_book_requirements()
                section.invalidate_recordset(["book_requirement_ids"])
            section._check_ready_for_book_purchase()

            # Prevent duplicate RFQs for same section/subject still open.
            conflicting = section.book_requirement_ids.filtered(
                lambda r: r.state == "rfq"
                and r.purchase_order_id
                and r.purchase_order_id.state not in ("cancel",)
            )
            ready = section.book_requirement_ids.filtered(
                lambda r: r.state in ("draft", "ready")
                and float_compare(r.purchase_qty, 0.0, precision_digits=2) > 0
            )
            if conflicting and not ready:
                raise UserError(
                    _(
                        "Book purchase RFQs already exist for this section (%s). "
                        "Cancel the draft RFQ or reset requirements before creating another purchase."
                    )
                    % ", ".join(conflicting.mapped("purchase_order_id").mapped("display_name"))
                )
            overlap_subjects = conflicting.mapped("subject_id") & ready.mapped("subject_id")
            if overlap_subjects:
                raise UserError(
                    _(
                        "RFQ already exists for subject(s) %s on this section. "
                        "Cancel the draft RFQ or reset requirements before creating another purchase."
                    )
                    % ", ".join(overlap_subjects.mapped("name"))
                )

            by_vendor = defaultdict(lambda: self.env["university.book.requirement"])
            for req in ready:
                by_vendor[req.vendor_id] |= req

            PurchaseOrder = self.env["purchase.order"]
            for vendor, requirements in by_vendor.items():
                order = PurchaseOrder.create({
                    "partner_id": vendor.id,
                    "company_id": self.env.company.id,
                    "class_section_id": section.id,
                    "origin": _("Book procurement: %s") % section.display_name,
                })
                for req in requirements:
                    # Refresh free qty at RFQ time for safer multi-section concurrency.
                    warehouse = req.warehouse_id or section._get_book_procurement_warehouse()
                    live_free = section._get_product_free_qty(req.product_id, warehouse)
                    usable = min(live_free, req.required_qty)
                    purchase_qty = max(0.0, req.required_qty - usable)
                    if float_compare(purchase_qty, 0.0, precision_digits=2) <= 0:
                        req.write({
                            "available_qty": usable,
                            "purchase_qty": 0.0,
                            "state": "ready",
                        })
                        continue
                    price, uom = section._get_seller_price(req.product_id, vendor, purchase_qty)
                    line_vals = {
                        "order_id": order.id,
                        "product_id": req.product_id.id,
                        "name": _("%(subject)s — %(product)s")
                        % {"subject": req.subject_id.display_name, "product": req.product_id.display_name},
                        "product_qty": purchase_qty,
                        "price_unit": price,
                        "date_planned": fields.Datetime.now(),
                    }
                    if "product_uom_id" in self.env["purchase.order.line"]._fields and uom:
                        line_vals["product_uom_id"] = uom.id
                    elif "product_uom" in self.env["purchase.order.line"]._fields and uom:
                        line_vals["product_uom"] = uom.id
                    line = self.env["purchase.order.line"].create(line_vals)
                    req.write({
                        "available_qty": usable,
                        "purchase_qty": purchase_qty,
                        "purchase_line_id": line.id,
                        "state": "rfq",
                    })
                if not order.order_line:
                    order.unlink()
                    continue
                created_orders |= order

        if not created_orders:
            raise UserError(_("No purchase RFQs were created. Stock may already cover all needs."))

        action = {
            "type": "ir.actions.act_window",
            "name": _("Book Purchase RFQs"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", created_orders.ids)],
            "target": "current",
        }
        if len(created_orders) == 1:
            action.update({"view_mode": "form", "res_id": created_orders.id})
        return action

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Orders - %s") % self.name,
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("class_section_id", "=", self.id)],
            "context": {
                "default_class_section_id": self.id,
                "default_partner_id": self.book_vendor_id.id if self.book_vendor_id else False,
            },
        }

    def action_view_book_requirements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Book Requirements - %s") % self.name,
            "res_model": "university.book.requirement",
            "view_mode": "list,form",
            "domain": [("section_id", "=", self.id)],
            "context": {"default_section_id": self.id},
        }

    def action_close_enrollment_for_books(self):
        """Set deadline to yesterday so enrollment is closed and procurement can start."""
        self._check_can_manage_book_procurement()
        yesterday = fields.Date.context_today(self) - timedelta(days=1)
        self.write({"enroll_deadline": yesterday})
        return True
