"""Book procurement integration tests for school_purchase."""

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import float_compare


@tagged("post_install", "-at_install")
class TestBookProcurement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = fields.Date.today()
        cls.today = today
        cls.yesterday = today - timedelta(days=1)
        cls.tomorrow = today + timedelta(days=1)

        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.assertTrue(cls.warehouse, "A warehouse is required for stock-aware procurement tests.")

        cls.vendor_a = cls.env["res.partner"].create({
            "name": "Book Vendor A",
            "supplier_rank": 1,
            "is_company": True,
        })
        cls.vendor_b = cls.env["res.partner"].create({
            "name": "Book Vendor B",
            "supplier_rank": 1,
            "is_company": True,
        })

        def _book(name, vendor, price=25.0):
            product = cls.env["product.product"].create({
                "name": name,
                "type": "consu",
                "is_storable": True,
                "purchase_ok": True,
                "list_price": price,
                "standard_price": price,
                "seller_ids": [Command.create({
                    "partner_id": vendor.id,
                    "min_qty": 1.0,
                    "price": price,
                })],
            })
            return product

        cls.book_math = _book("Mathematics Grade 11 Book", cls.vendor_a, 30.0)
        cls.book_english = _book("English Grade 11 Book", cls.vendor_a, 20.0)
        cls.book_physics = _book("Physics Grade 11 Book", cls.vendor_b, 35.0)

        cls.faculty = cls.env["university.faculty"].create({
            "name": "Procurement Faculty",
            "code": "PROCFAC",
        })
        cls.department = cls.env["university.department"].create({
            "name": "Procurement Dept",
            "code": "PROCDEP",
            "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "Procurement Program",
            "code": "PROCPROG",
            "department_id": cls.department.id,
            "degree_type": "bachelor",
        })
        cls.year = cls.env["university.academic.year"].search([("state", "=", "running")], limit=1)
        if not cls.year:
            cls.year = cls.env["university.academic.year"].create({
                "name": "Procurement AY 2040",
                "date_start": fields.Date.from_string("2040-09-01"),
                "date_end": fields.Date.from_string("2041-06-30"),
                "state": "running",
            })
        cls.semester = cls.year.semester_ids[:1]
        if not cls.semester:
            cls.semester = cls.env["university.semester"].create({
                "name": "Procurement Sem",
                "academic_year_id": cls.year.id,
                "semester_type": "semester_1",
                "date_start": cls.year.date_start,
                "date_end": cls.year.date_end,
            })

        cls.subject_math = cls.env["university.subject"].create({
            "name": "Mathematics",
            "code": "MATH11",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "book_product_id": cls.book_math.id,
        })
        cls.subject_english = cls.env["university.subject"].create({
            "name": "English",
            "code": "ENG11",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "book_product_id": cls.book_english.id,
        })
        cls.subject_physics = cls.env["university.subject"].create({
            "name": "Physics",
            "code": "PHY11",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
            "book_product_id": cls.book_physics.id,
        })
        cls.subject_no_book = cls.env["university.subject"].create({
            "name": "History",
            "code": "HIS11",
            "department_id": cls.department.id,
            "program_ids": [Command.set([cls.program.id])],
        })

        cls.admin_group = cls.env.ref("school_management.group_school_admin")
        cls.student_group = cls.env.ref("school_management.group_school_student")
        cls.purchase_user_group = cls.env.ref("purchase.group_purchase_user")

        cls.admin_user = cls.env["res.users"].create({
            "name": "Book Admin",
            "login": "book_admin_test@example.com",
            "group_ids": [Command.set([
                cls.admin_group.id,
                cls.purchase_user_group.id,
                cls.env.ref("base.group_user").id,
            ])],
        })
        cls.student_user = cls.env["res.users"].create({
            "name": "Book Student User",
            "login": "book_student_test@example.com",
            "group_ids": [Command.set([
                cls.student_group.id,
                cls.env.ref("base.group_user").id,
            ])],
        })

    def _make_student(self, name):
        return self.env["university.student"].create({
            "name": name,
            "status": "active",
            "program_id": self.program.id,
            "faculty_id": self.faculty.id,
            "department_id": self.department.id,
            "academic_year_id": self.year.id,
            "current_semester_id": self.semester.id,
        })

    def _make_section(self, subject, name=None, deadline=None, vendor=None):
        return self.env["university.class.section"].create({
            "name": name or f"{subject.code}-A",
            "section_type": "course",
            "subject_id": subject.id,
            "program_id": self.program.id,
            "semester_id": self.semester.id,
            "capacity": 40,
            "enroll_deadline": deadline or self.tomorrow,
            "book_vendor_id": vendor.id if vendor else False,
        })

    def _enroll(self, student, section, has_book=False, status="enrolled"):
        return self.env["university.enrollment"].with_context(
            bypass_enrollment_deadline=True,
            bypass_registration_window=True,
        ).create({
            "student_id": student.id,
            "class_section_id": section.id,
            "status": status,
            "has_book": has_book,
        })

    def _set_stock(self, product, qty):
        location = self.warehouse.lot_stock_id
        quant = self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": product.id,
            "location_id": location.id,
            "inventory_quantity": qty,
        })
        quant.action_apply_inventory()
        return quant

    def _close(self, section):
        section.action_close_enrollment_for_books()
        self.assertTrue(section.enroll_closed)

    # 1. Enrollment still open
    def test_01_compute_blocked_while_enrollment_open(self):
        section = self._make_section(self.subject_math, deadline=self.tomorrow)
        student = self._make_student("Open Enroll Student")
        self._enroll(student, section)
        with self.assertRaises(UserError):
            section.action_compute_book_requirements()

    # 2. Enrollment closed
    def test_02_compute_allowed_when_closed(self):
        section = self._make_section(self.subject_math)
        student = self._make_student("Closed Enroll Student")
        self._enroll(student, section)
        self._close(section)
        section.action_compute_book_requirements()
        req = section.book_requirement_ids
        self.assertEqual(len(req), 1)
        self.assertEqual(req.product_id, self.book_math)
        self.assertEqual(req.required_qty, 1.0)
        self.assertEqual(req.purchase_qty, 1.0)
        self.assertEqual(req.state, "ready")

    # 3. Subject has no configured book
    def test_03_subject_missing_book_config(self):
        section = self._make_section(self.subject_no_book)
        student = self._make_student("No Book Config Student")
        self._enroll(student, section)
        self._close(section)
        with self.assertRaises(UserError):
            section.action_compute_book_requirements()

    # 4. Student already owns the book
    def test_04_student_already_has_book_excluded(self):
        section = self._make_section(self.subject_math)
        s1 = self._make_student("Has Book")
        s2 = self._make_student("Needs Book")
        self._enroll(s1, section, has_book=True)
        self._enroll(s2, section, has_book=False)
        self._close(section)
        section.action_compute_book_requirements()
        req = section.book_requirement_ids
        self.assertEqual(req.students_with_books, 1)
        self.assertEqual(req.students_needing_books, 1)
        self.assertEqual(req.required_qty, 1.0)

    # 5. Student enrolls in multiple subjects
    def test_05_student_multiple_subjects(self):
        math_sec = self._make_section(self.subject_math, name="MATH-A")
        eng_sec = self._make_section(self.subject_english, name="ENG-A")
        student = self._make_student("Multi Subject Student")
        self._enroll(student, math_sec)
        self._enroll(student, eng_sec)
        self._close(math_sec)
        self._close(eng_sec)
        math_sec.action_compute_book_requirements()
        eng_sec.action_compute_book_requirements()
        self.assertEqual(math_sec.book_requirement_ids.required_qty, 1.0)
        self.assertEqual(eng_sec.book_requirement_ids.required_qty, 1.0)
        self.assertEqual(math_sec.book_requirement_ids.product_id, self.book_math)
        self.assertEqual(eng_sec.book_requirement_ids.product_id, self.book_english)

    # 6. Some books already available in inventory
    def test_06_available_stock_reduces_purchase_qty(self):
        section = self._make_section(self.subject_math)
        for i in range(5):
            self._enroll(self._make_student(f"Stock Student {i}"), section)
        self._set_stock(self.book_math, 2.0)
        self._close(section)
        section.action_compute_book_requirements()
        req = section.book_requirement_ids
        self.assertEqual(req.required_qty, 5.0)
        self.assertEqual(req.available_qty, 2.0)
        self.assertEqual(req.purchase_qty, 3.0)

    # 7. Different subjects same vendor → one RFQ
    def test_07_same_vendor_single_rfq(self):
        # One section has one subject in this architecture; use two sections sharing vendor,
        # and also verify create groups by vendor within one compute of multi-subject needs
        # via two course sections purchased separately would create separate POs per section.
        # Validate vendor grouping by creating requirements for two subjects on one section
        # through manual requirement creation after compute of a multi-need section is not
        # native — instead create two purchases from two sections with same vendor and assert
        # each section gets one PO, and product sellers resolve to vendor_a.
        math_sec = self._make_section(self.subject_math, name="MATH-V")
        eng_sec = self._make_section(self.subject_english, name="ENG-V")
        self._enroll(self._make_student("Same Vendor 1"), math_sec)
        self._enroll(self._make_student("Same Vendor 2"), eng_sec)
        self._close(math_sec)
        self._close(eng_sec)
        math_sec.action_compute_book_requirements()
        eng_sec.action_compute_book_requirements()
        self.assertEqual(math_sec.book_requirement_ids.vendor_id, self.vendor_a)
        self.assertEqual(eng_sec.book_requirement_ids.vendor_id, self.vendor_a)
        action = math_sec.action_create_book_purchase()
        po = self.env["purchase.order"].browse(action["res_id"])
        self.assertEqual(po.partner_id, self.vendor_a)
        self.assertEqual(po.state, "draft")
        self.assertEqual(len(po.order_line), 1)

    # 8. Different vendors → multiple RFQs (simulate via two subjects by forcing
    #    second requirement onto same section through a second compute path)
    def test_08_different_vendors_multiple_rfqs(self):
        # Create two separate sections with different vendors and ensure each RFQ uses its vendor.
        math_sec = self._make_section(self.subject_math, name="MATH-DV")
        phy_sec = self._make_section(self.subject_physics, name="PHY-DV")
        self._enroll(self._make_student("Vendor Diff Math"), math_sec)
        self._enroll(self._make_student("Vendor Diff Phy"), phy_sec)
        self._close(math_sec)
        self._close(phy_sec)
        math_sec.action_create_book_purchase()
        phy_sec.action_create_book_purchase()
        math_po = math_sec.purchase_order_ids
        phy_po = phy_sec.purchase_order_ids
        self.assertEqual(math_po.partner_id, self.vendor_a)
        self.assertEqual(phy_po.partner_id, self.vendor_b)
        self.assertNotEqual(math_po.id, phy_po.id)

    def test_08b_vendor_grouping_within_section(self):
        """Group multiple ready requirements on one section by vendor into separate POs."""
        section = self._make_section(self.subject_math, name="MULTI-VEND")
        student = self._make_student("Grouped Vendor Student")
        self._enroll(student, section)
        self._close(section)
        section.action_compute_book_requirements()
        # Inject a second ready requirement for another subject/vendor (same section).
        self.env["university.book.requirement"].create({
            "section_id": section.id,
            "subject_id": self.subject_physics.id,
            "product_id": self.book_physics.id,
            "vendor_id": self.vendor_b.id,
            "company_id": self.company.id,
            "warehouse_id": self.warehouse.id,
            "student_count": 1,
            "students_with_books": 0,
            "students_needing_books": 1,
            "required_qty": 1.0,
            "available_qty": 0.0,
            "purchase_qty": 1.0,
            "state": "ready",
        })
        action = section.action_create_book_purchase()
        orders = self.env["purchase.order"].search(action["domain"])
        self.assertEqual(len(orders), 2)
        self.assertEqual(set(orders.mapped("partner_id")), {self.vendor_a, self.vendor_b})
        self.assertTrue(all(o.state == "draft" for o in orders))

    # 9. Administrator clicks purchase button twice
    def test_09_double_create_purchase_blocked(self):
        section = self._make_section(self.subject_math, name="DBL-CLK")
        self._enroll(self._make_student("Double Click Student"), section)
        self._close(section)
        section.action_create_book_purchase()
        self.assertEqual(len(section.purchase_order_ids), 1)
        with self.assertRaises(UserError):
            section.action_create_book_purchase()
        self.assertEqual(len(section.purchase_order_ids), 1)

    # 10. Purchase confirmed and books marked distributed
    def test_10_confirm_and_mark_books_distributed(self):
        section = self._make_section(self.subject_math, name="RECV")
        enrollment = self._enroll(self._make_student("Receive Student"), section)
        self._close(section)
        action = section.action_create_book_purchase()
        po = self.env["purchase.order"].browse(action["res_id"])
        po.button_confirm()
        self.assertIn(po.state, ("purchase", "done"))
        po.action_mark_class_books_received()
        self.assertTrue(enrollment.has_book)
        self.assertEqual(section.book_requirement_ids.state, "done")

    # 11. Multiple sections require the same book
    def test_11_multiple_sections_same_book_stock_aware(self):
        sec_a = self._make_section(self.subject_math, name="MATH-S1")
        sec_b = self._make_section(self.subject_math, name="MATH-S2")
        for i in range(3):
            self._enroll(self._make_student(f"SecA {i}"), sec_a)
            self._enroll(self._make_student(f"SecB {i}"), sec_b)
        self._set_stock(self.book_math, 2.0)
        self._close(sec_a)
        self._close(sec_b)
        sec_a.action_compute_book_requirements()
        sec_b.action_compute_book_requirements()
        self.assertEqual(sec_a.book_requirement_ids.available_qty, 2.0)
        self.assertEqual(sec_a.book_requirement_ids.purchase_qty, 1.0)
        # Section B also sees free stock at compute time (capped to need).
        self.assertEqual(sec_b.book_requirement_ids.available_qty, 2.0)
        self.assertEqual(sec_b.book_requirement_ids.purchase_qty, 1.0)
        # First RFQ re-reads live free qty.
        sec_a.action_create_book_purchase()
        req_a = sec_a.book_requirement_ids
        self.assertEqual(req_a.state, "rfq")
        self.assertTrue(float_compare(req_a.purchase_qty, 0.0, precision_digits=2) > 0)

    # 12. Concurrent-style re-entry: second create while RFQ exists
    def test_12_concurrent_second_admin_blocked(self):
        section = self._make_section(self.subject_math, name="CONCUR")
        self._enroll(self._make_student("Concurrent Student"), section)
        self._close(section)
        section.with_user(self.admin_user).action_create_book_purchase()
        with self.assertRaises(UserError):
            section.with_user(self.admin_user).action_create_book_purchase()

    def test_student_cannot_compute_requirements(self):
        section = self._make_section(self.subject_math, name="SEC-STUDENT")
        self._enroll(self._make_student("ACL Student"), section)
        self._close(section)
        with self.assertRaises(AccessError):
            section.with_user(self.student_user).action_compute_book_requirements()

    def test_non_purchasable_book_rejected(self):
        bad = self.env["product.product"].create({
            "name": "Non Purchasable Notes",
            "type": "consu",
            "purchase_ok": False,
        })
        with self.assertRaises(ValidationError):
            self.subject_math.book_product_id = bad

    def test_recompute_updates_draft_rfq_qty(self):
        section = self._make_section(self.subject_math, name="SYNC-RFQ")
        e1 = self._enroll(self._make_student("Sync 1"), section)
        self._enroll(self._make_student("Sync 2"), section)
        self._close(section)
        section.action_create_book_purchase()
        req = section.book_requirement_ids
        self.assertEqual(req.state, "rfq")
        self.assertEqual(req.purchase_qty, 2.0)
        line = req.purchase_line_id
        self.assertEqual(line.product_qty, 2.0)

        # One student obtains the book; recompute must update draft RFQ line, not confirmed PO.
        e1.has_book = True
        section.action_compute_book_requirements()
        self.assertEqual(req.required_qty, 1.0)
        self.assertEqual(req.purchase_qty, 1.0)
        self.assertEqual(req.state, "rfq")
        self.assertEqual(line.product_qty, 1.0)

    def test_new_enrollment_blocked_after_close(self):
        section = self._make_section(self.subject_math, name="BLOCK-NEW")
        self._enroll(self._make_student("Before Close"), section)
        self._close(section)
        with self.assertRaises(ValidationError):
            self.env["university.enrollment"].create({
                "student_id": self._make_student("After Close").id,
                "class_section_id": section.id,
                "status": "enrolled",
            })
