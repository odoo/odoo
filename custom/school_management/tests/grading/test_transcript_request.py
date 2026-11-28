from datetime import timedelta
from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestTranscriptRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Security groups
        cls.group_student = cls.env.ref("school_management.group_school_student")
        cls.group_registrar = cls.env.ref("school_management.group_school_registrar")
        cls.group_admin = cls.env.ref("school_management.group_school_admin")

        # Create users
        cls.student_user = cls.env["res.users"].create({
            "name": "Test Student User",
            "login": "test_student_req@example.com",
            "email": "test_student_req@example.com",
            "group_ids": [Command.set([cls.group_student.id])],
        })
        cls.registrar_user = cls.env["res.users"].create({
            "name": "Test Registrar User",
            "login": "test_registrar_req@example.com",
            "email": "test_registrar_req@example.com",
            "group_ids": [Command.set([cls.group_registrar.id])],
        })
        cls.admin_user = cls.env["res.users"].create({
            "name": "Test Admin User",
            "login": "test_admin_req@example.com",
            "email": "test_admin_req@example.com",
            "group_ids": [Command.set([cls.group_admin.id])],
        })

        # Academic infrastructure
        cls.faculty = cls.env["university.faculty"].create({
            "name": "Faculty of Testing",
            "code": "FTEST-TR",
        })
        cls.department = cls.env["university.department"].create({
            "name": "Testing Dept",
            "code": "DTEST-TR",
            "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": "BS Testing Science",
            "code": "PTEST-TR",
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
            "degree_type": "bachelor",
        })
        cls.academic_year = cls.env["university.academic.year"].create({
            "name": "2026-2027 Test",
            "date_start": "2026-09-01",
            "date_end": "2027-06-30",
        })
        cls.semester = cls.env["university.semester"].create({
            "name": "Fall 2026 Test",
            "academic_year_id": cls.academic_year.id,
            "date_start": "2026-09-01",
            "date_end": "2026-12-31",
        })

        # Student record
        cls.student = cls.env["university.student"].create({
            "name": "Alice Requestor",
            "student_id": "STD-REQ-999",
            "email": "test_student_req@example.com",
            "user_id": cls.student_user.id,
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
            "program_id": cls.program.id,
            "academic_year_id": cls.academic_year.id,
            "current_semester_id": cls.semester.id,
            "status": "active",
        })

        cls.grade_scale = cls.env["university.grade.scale"].create({
            "name": "Standard Scale Test",
        })
        cls.report_card = cls.env["university.report.card"].create({
            "student_id": cls.student.id,
            "academic_year_id": cls.academic_year.id,
            "semester_id": cls.semester.id,
            "grade_scale_id": cls.grade_scale.id,
            "state": "approved",
        })

        cls.transcript = cls.env["university.transcript"].create({
            "student_id": cls.student.id,
            "state": "approved",
            "cumulative_gpa": 3.75,
            "total_credits": 15,
        })

    def test_01_full_workflow(self):
        """Test happy path from draft to delivered."""
        # 1. Student creates request
        req = self.env["university.transcript.request"].with_user(self.student_user).create({
            "student_id": self.student.id,
            "request_type": "official",
            "copies": 2,
            "purpose": "employment",
            "delivery_method": "download",
            "recipient": "Tech Corp HR",
        })
        self.assertEqual(req.state, "draft")
        self.assertTrue(req.name.startswith("TR-"))
        self.assertEqual(req.program_id, self.program)

        # 2. Student submits
        req.with_user(self.student_user).action_submit()
        self.assertEqual(req.state, "submitted")

        # 3. Registrar approves
        req.with_user(self.registrar_user).action_approve()
        self.assertEqual(req.state, "approved")
        self.assertEqual(req.approved_by, self.registrar_user)
        self.assertTrue(req.approved_date)

        # 4. Registrar issues
        req.with_user(self.registrar_user).action_issue()
        self.assertEqual(req.state, "issued")
        self.assertTrue(req.transcript_id)
        self.assertTrue(req.verification_code)

        # 5. Registrar delivers
        req.with_user(self.registrar_user).action_deliver()
        self.assertEqual(req.state, "delivered")

    def test_02_student_cannot_approve_or_issue(self):
        """A student must never be allowed to approve or issue a transcript."""
        req = self.env["university.transcript.request"].with_user(self.student_user).create({
            "student_id": self.student.id,
            "request_type": "unofficial",
            "copies": 1,
            "purpose": "scholarship",
            "delivery_method": "download",
        })
        req.with_user(self.student_user).action_submit()

        # Student attempting approve
        with self.assertRaises(UserError):
            req.with_user(self.student_user).action_approve()

        # Student attempting write to administrative fields
        with self.assertRaises(UserError):
            req.with_user(self.student_user).write({"state": "approved"})

    def test_03_rejection_requires_reason(self):
        """Rejection must mandate an explanation."""
        req = self.env["university.transcript.request"].with_user(self.student_user).create({
            "student_id": self.student.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "visa",
            "delivery_method": "download",
        })
        req.action_submit()

        # Rejecting without reason raises error
        with self.assertRaises(UserError):
            req.with_user(self.registrar_user).action_reject(reason="")

        # Rejecting with reason succeeds
        req.with_user(self.registrar_user).action_reject(reason="Missing identity verification")
        self.assertEqual(req.state, "rejected")
        self.assertEqual(req.reject_reason, "Missing identity verification")

    def test_04_holds_block_approval(self):
        """Active student holds must block approval."""
        yesterday = fields.Date.today() - timedelta(days=1)
        fee = self.env["university.fee"].create({
            "student_id": self.student.id,
            "due_date": yesterday,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Tuition",
            "amount": 500.0,
        })

        req = self.env["university.transcript.request"].create({
            "student_id": self.student.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "transfer",
            "delivery_method": "download",
        })
        req.action_submit()

        # Approval must fail due to overdue balance hold
        holds = req._get_transcript_holds()
        self.assertTrue(len(holds) > 0)
        self.assertTrue(any(h["code"] == "financial" and h["severity"] == "block" for h in holds))
        with self.assertRaises(UserError):
            req.with_user(self.registrar_user).action_approve()

    def test_05_cancellation_constraints(self):
        """Students can only cancel draft or submitted requests."""
        req = self.env["university.transcript.request"].with_user(self.student_user).create({
            "student_id": self.student.id,
            "request_type": "unofficial",
            "copies": 1,
            "purpose": "other",
            "purpose_other": "Personal records",
            "delivery_method": "download",
        })
        req.action_submit()
        req.action_cancel()
        self.assertEqual(req.state, "cancelled")

    def test_06_duplicate_open_request_blocked(self):
        """A student cannot have two open requests of the same request_type."""
        self.env["university.transcript.request"].create({
            "student_id": self.student.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "employment",
            "delivery_method": "download",
            "state": "submitted",
        })

        with self.assertRaises(ValidationError):
            self.env["university.transcript.request"].create({
                "student_id": self.student.id,
                "request_type": "official",
                "copies": 1,
                "purpose": "visa",
                "delivery_method": "download",
                "state": "draft",
            })

    def test_acceptance_01_two_holds_official(self):
        """Acceptance 1: Student with no finalized report card and an overdue 500.00 invoice, Official Transcript.
        Banner/method shows exactly TWO holds (grades, financial); the financial one appears once.
        Approve is blocked with both listed.
        """
        # Create student Bob with NO report cards
        bob = self.env["university.student"].create({
            "name": "Bob HoldStudent",
            "student_id": "STD-BOB-001",
            "program_id": self.program.id,
            "status": "active",
        })
        # Overdue fee of 500.00
        yesterday = fields.Date.today() - timedelta(days=2)
        fee = self.env["university.fee"].create({
            "student_id": bob.id,
            "due_date": yesterday,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Tuition Fee",
            "amount": 500.0,
        })
        self.assertEqual(fee.balance, 500.0)

        req = self.env["university.transcript.request"].create({
            "student_id": bob.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "employment",
            "delivery_method": "download",
        })
        req.action_submit()

        holds = req._get_transcript_holds()
        # Exactly TWO holds: grades and financial (financial appears once)
        self.assertEqual(len(holds), 2)
        codes = [h["code"] for h in holds]
        self.assertIn("no_grades", codes)
        self.assertIn("financial", codes)
        self.assertEqual(codes.count("financial"), 1)
        self.assertEqual(codes.count("no_grades"), 1)

        # Both are severity "block"
        self.assertTrue(all(h["severity"] == "block" for h in holds))

        # Check badges
        self.assertEqual(req.grades_status, "Grades: Missing")
        self.assertIn("Overdue 500.00", req.finance_status)

        # Approve is blocked with both listed
        with self.assertRaises(UserError) as cm:
            req.with_user(self.registrar_user).action_approve()
        err_msg = str(cm.exception)
        self.assertIn("No finalized report cards found for Bob HoldStudent", err_msg)
        self.assertIn("Outstanding tuition/fee balance of 500.00", err_msg)

    def test_acceptance_02_unofficial_copy_warning(self):
        """Acceptance 2: Same student, unofficial copy: financial shows only as a warning; grades still blocks."""
        bob = self.env["university.student"].create({
            "name": "Bob Unofficial",
            "student_id": "STD-BOB-002",
            "program_id": self.program.id,
            "status": "active",
        })
        yesterday = fields.Date.today() - timedelta(days=2)
        fee = self.env["university.fee"].create({
            "student_id": bob.id,
            "due_date": yesterday,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Tuition Fee",
            "amount": 500.0,
        })

        req = self.env["university.transcript.request"].create({
            "student_id": bob.id,
            "request_type": "unofficial",
            "copies": 1,
            "purpose": "other",
            "purpose_other": "Self-check",
            "delivery_method": "download",
        })
        req.action_submit()

        holds = req._get_transcript_holds()
        self.assertEqual(len(holds), 2)

        grades_hold = next(h for h in holds if h["code"] == "no_grades")
        financial_hold = next(h for h in holds if h["code"] == "financial")

        self.assertEqual(grades_hold["severity"], "block")
        self.assertEqual(financial_hold["severity"], "warning")

        # Approve is blocked with grades, but financial warning does NOT block
        with self.assertRaises(UserError) as cm:
            req.with_user(self.registrar_user).action_approve()
        err_msg = str(cm.exception)
        self.assertIn("No finalized report cards found", err_msg)
        self.assertNotIn("Outstanding tuition/fee balance", err_msg)

    def test_acceptance_03_finalize_grades_and_pay_invoice(self):
        """Acceptance 3: Finalize a report card and pay the invoice, then Approve: succeeds."""
        charlie = self.env["university.student"].create({
            "name": "Charlie Clean",
            "student_id": "STD-CHARLIE-001",
            "program_id": self.program.id,
            "status": "active",
        })
        yesterday = fields.Date.today() - timedelta(days=2)
        fee = self.env["university.fee"].create({
            "student_id": charlie.id,
            "due_date": yesterday,
            "state": "posted",
        })
        line = self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Tuition Fee",
            "amount": 500.0,
        })

        # Draft report card
        rc = self.env["university.report.card"].create({
            "student_id": charlie.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "grade_scale_id": self.grade_scale.id,
            "state": "draft",
        })

        req = self.env["university.transcript.request"].create({
            "student_id": charlie.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "scholarship",
            "delivery_method": "download",
        })
        req.action_submit()

        # Blocked initially
        self.assertEqual(len(req._get_transcript_holds()), 2)

        # Now finalize report card and pay invoice
        rc.write({"state": "approved"})
        fee.write({"state": "paid"})
        line.write({"amount": 0.0})
        fee._compute_totals()

        # Fresh holds should now be empty
        self.assertEqual(len(req._get_transcript_holds()), 0)

        # Approve succeeds
        req.with_user(self.registrar_user).action_approve()
        self.assertEqual(req.state, "approved")

    def test_acceptance_04_unpaid_not_due_invoice(self):
        """Acceptance 4: Unpaid but NOT yet due invoice: no financial hold."""
        dave = self.env["university.student"].create({
            "name": "Dave FutureDue",
            "student_id": "STD-DAVE-001",
            "program_id": self.program.id,
            "status": "active",
        })
        self.env["university.report.card"].create({
            "student_id": dave.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "grade_scale_id": self.grade_scale.id,
            "state": "generated",
        })

        # Invoice due in the future
        tomorrow = fields.Date.today() + timedelta(days=10)
        fee = self.env["university.fee"].create({
            "student_id": dave.id,
            "due_date": tomorrow,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Upcoming Tuition",
            "amount": 1000.0,
        })

        req = self.env["university.transcript.request"].create({
            "student_id": dave.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "transfer",
            "delivery_method": "download",
        })
        req.action_submit()

        holds = req._get_transcript_holds()
        # No financial hold!
        self.assertFalse(any(h["code"] == "financial" for h in holds))
        self.assertEqual(len(holds), 0)

        # Approve succeeds
        req.with_user(self.registrar_user).action_approve()
        self.assertEqual(req.state, "approved")

    def test_acceptance_05_balance_below_threshold(self):
        """Acceptance 5: Balance below the threshold setting: no financial hold."""
        eve = self.env["university.student"].create({
            "name": "Eve SmallBalance",
            "student_id": "STD-EVE-001",
            "program_id": self.program.id,
            "status": "active",
        })
        self.env["university.report.card"].create({
            "student_id": eve.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "grade_scale_id": self.grade_scale.id,
            "state": "approved",
        })

        yesterday = fields.Date.today() - timedelta(days=1)
        fee = self.env["university.fee"].create({
            "student_id": eve.id,
            "due_date": yesterday,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Library Fine",
            "amount": 25.0,
        })

        # Set threshold to 50.00
        self.env["ir.config_parameter"].sudo().set_param(
            "school_management.transcript_hold_min_balance", "50.0"
        )

        req = self.env["university.transcript.request"].create({
            "student_id": eve.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "visa",
            "delivery_method": "download",
        })
        req.action_submit()

        holds = req._get_transcript_holds()
        self.assertEqual(len(holds), 0)

        # Approve succeeds
        req.with_user(self.registrar_user).action_approve()
        self.assertEqual(req.state, "approved")

        # Clean up threshold
        self.env["ir.config_parameter"].sudo().set_param(
            "school_management.transcript_hold_min_balance", "0.0"
        )

    def test_acceptance_06_admin_approve_anyway_override(self):
        """Acceptance 6: Admin uses Approve Anyway with a reason: request becomes Approved,
        chatter shows the overridden holds + reason + user, and a non-admin user cannot perform override.
        """
        frank = self.env["university.student"].create({
            "name": "Frank Override",
            "student_id": "STD-FRANK-001",
            "program_id": self.program.id,
            "status": "active",
        })
        yesterday = fields.Date.today() - timedelta(days=5)
        fee = self.env["university.fee"].create({
            "student_id": frank.id,
            "due_date": yesterday,
            "state": "posted",
        })
        self.env["university.fee.line"].create({
            "fee_id": fee.id,
            "name": "Tuition",
            "amount": 1200.0,
        })

        req = self.env["university.transcript.request"].create({
            "student_id": frank.id,
            "request_type": "official",
            "copies": 1,
            "purpose": "scholarship",
            "delivery_method": "download",
        })
        req.action_submit()

        # Regular approve is blocked
        with self.assertRaises(UserError):
            req.with_user(self.registrar_user).action_approve()

        # Student user attempting override fails
        with self.assertRaises(UserError):
            req.with_user(self.student_user).action_confirm_override("Dean special permission")

        # Admin override requires at least 10 characters
        with self.assertRaises(ValidationError):
            wizard = self.env["university.transcript.request.override.wizard"].with_user(self.admin_user).create({
                "request_id": req.id,
                "reason": "Too short",
            })
            wizard.action_confirm_override()

        # Valid override by admin
        reason_text = "Authorized by Academic Senate due to scholarship application deadline."
        wizard = self.env["university.transcript.request.override.wizard"].with_user(self.admin_user).create({
            "request_id": req.id,
            "reason": reason_text,
        })
        wizard.action_confirm_override()

        self.assertEqual(req.state, "approved")
        self.assertEqual(req.override_user_id, self.admin_user)
        self.assertEqual(req.override_reason, reason_text)
        self.assertTrue(req.override_date)

        # Verify chatter log
        messages = req.message_ids
        override_msg = messages.filtered(lambda m: "Administrative Override" in (m.body or ""))
        self.assertTrue(override_msg)
        self.assertIn("no_grades", override_msg.body)
        self.assertIn("financial", override_msg.body)
        self.assertIn(reason_text, override_msg.body)
        self.assertIn(self.admin_user.name, override_msg.body)
