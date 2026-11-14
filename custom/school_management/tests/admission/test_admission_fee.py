import secrets
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase


class TestAdmissionFee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_group = cls.env.ref("school_management.group_school_admin")
        cls.env.user.group_ids = [Command.link(cls.admin_group.id)]

        # Infrastructure
        cls.faculty = cls.env["university.faculty"].create({
            "name": f"Faculty of Nursing {secrets.token_hex(3)}",
            "code": f"FN_{secrets.token_hex(3).upper()}",
        })
        cls.department = cls.env["university.department"].create({
            "name": f"Nursing Dept {secrets.token_hex(3)}",
            "code": f"ND_{secrets.token_hex(3).upper()}",
            "faculty_id": cls.faculty.id,
        })
        cls.program = cls.env["university.program"].create({
            "name": f"Bachelor of Science in Nursing {secrets.token_hex(3)}",
            "code": f"BSN_{secrets.token_hex(3).upper()}",
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
        })
        cls.other_program = cls.env["university.program"].create({
            "name": f"Bachelor of Computer Science {secrets.token_hex(3)}",
            "code": f"BCS_{secrets.token_hex(3).upper()}",
            "faculty_id": cls.faculty.id,
            "department_id": cls.department.id,
        })

        cls.academic_year = cls.env["university.academic.year"].search([
            ("name", "=", "2025-2026")
        ], limit=1)
        if not cls.academic_year:
            cls.academic_year = cls.env["university.academic.year"].create({
                "name": f"AY_{secrets.token_hex(4)}",
                "date_start": "2025-09-01",
                "date_end": "2026-06-30",
            })

        cls.semester_1 = cls.env["university.semester"].search([
            ("academic_year_id", "=", cls.academic_year.id),
            ("semester_type", "=", "semester_1"),
        ], limit=1)
        if not cls.semester_1:
            cls.semester_1 = cls.env["university.semester"].create({
                "name": f"Sem 1_{secrets.token_hex(3)}",
                "academic_year_id": cls.academic_year.id,
                "semester_type": "semester_1",
                "date_start": "2025-09-01",
                "date_end": "2026-01-31",
            })

        cls.semester_2 = cls.env["university.semester"].search([
            ("academic_year_id", "=", cls.academic_year.id),
            ("semester_type", "=", "semester_2"),
        ], limit=1)
        if not cls.semester_2:
            cls.semester_2 = cls.env["university.semester"].create({
                "name": f"Sem 2_{secrets.token_hex(3)}",
                "academic_year_id": cls.academic_year.id,
                "semester_type": "semester_2",
                "date_start": "2026-02-01",
                "date_end": "2026-06-30",
            })

    def setUp(self):
        super().setUp()
        self.FeeStructure = self.env["university.fee.structure"]
        self.Application = self.env["university.admission.application"]

    def _create_fee_structure(self, name, program, year, semester, amount=500.0, active=True):
        return self.FeeStructure.create({
            "name": name,
            "program_id": program.id if program else False,
            "academic_year_id": year.id if year else False,
            "semester_id": semester.id if semester else False,
            "active": active,
            "line_ids": [
                (0, 0, {"name": "Tuition Fee", "amount": amount}),
            ],
        })

    def test_01_one_matching_fee_structure_loads_automatically(self):
        """1. One matching Fee Structure: correct fee loads automatically."""
        fee_struct = self._create_fee_structure(
            f"BSN Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )

        app_form = Form(self.Application)
        app_form.applicant_name = "Jane Doe"
        app_form.program_id = self.program
        app_form.academic_year_id = self.academic_year
        app_form.semester_id = self.semester_1

        self.assertEqual(app_form.fee_structure_id, fee_struct)
        self.assertEqual(app_form.fee_amount, 500.0)

        app = app_form.save()
        self.assertEqual(app.fee_structure_id, fee_struct)
        self.assertEqual(app.fee_amount, 500.0)

    def test_02_no_matching_fee_structure_no_fee_selected(self):
        """2. No matching Fee Structure: no incorrect fee is selected."""
        # Create structure for different semester
        self._create_fee_structure(
            f"BSN Sem 2 Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_2,
            amount=600.0,
        )

        app_form = Form(self.Application)
        app_form.applicant_name = "Alice No Match"
        app_form.program_id = self.program
        app_form.academic_year_id = self.academic_year
        app_form.semester_id = self.semester_1

        # No fee structure should be selected for semester 1
        self.assertFalse(app_form.fee_structure_id)
        self.assertEqual(app_form.fee_amount, 0.0)

    def test_03_multiple_matching_fee_structures_handled_safely(self):
        """3. Multiple matching Fee Structures: ambiguity is handled safely."""
        self._create_fee_structure(
            f"BSN Variant A {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )
        self._create_fee_structure(
            f"BSN Variant B {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=700.0,
        )

        app = self.Application.new({
            "applicant_name": "Ambiguity Test",
            "program_id": self.program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester_1.id,
        })
        res = app._onchange_academic_fee_structure()

        self.assertFalse(app.fee_structure_id)
        self.assertEqual(app.fee_amount, 0.0)
        self.assertIsInstance(res, dict)
        self.assertIn("warning", res)

    def test_04_changing_program_or_semester_clears_previous_selection(self):
        """4. Changing the program or semester: the previous selection is cleared."""
        struct_nursing = self._create_fee_structure(
            f"BSN Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )

        app_form = Form(self.Application)
        app_form.applicant_name = "Switcher"
        app_form.program_id = self.program
        app_form.academic_year_id = self.academic_year
        app_form.semester_id = self.semester_1

        self.assertEqual(app_form.fee_structure_id, struct_nursing)
        self.assertEqual(app_form.fee_amount, 500.0)

        # Change to another program that has NO fee structure configured
        app_form.program_id = self.other_program
        self.assertFalse(app_form.fee_structure_id)
        self.assertEqual(app_form.fee_amount, 0.0)

        # Switch back to nursing
        app_form.program_id = self.program
        self.assertEqual(app_form.fee_structure_id, struct_nursing)

        # Switch semester to semester 2 (which has no fee structure)
        app_form.semester_id = self.semester_2
        self.assertFalse(app_form.fee_structure_id)
        self.assertEqual(app_form.fee_amount, 0.0)

    def test_05_confirming_application_without_required_fee_is_blocked(self):
        """5. Confirming an application without a required fee: confirmation is blocked."""
        app = self.Application.create({
            "applicant_name": "No Fee App",
            "email": f"nofee_{secrets.token_hex(3)}@example.com",
            "program_id": self.program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester_1.id,
            "fee_structure_id": False,
        })
        app.action_submit()
        app.action_approve()

        with self.assertRaises(ValidationError) as ctx:
            app.action_confirm()
        self.assertIn("fee structure", str(ctx.exception).lower())

    def test_06_confirming_valid_application_generates_invoice_and_lines(self):
        """6. Confirming a valid application: the correct invoice and fee lines are generated."""
        fee_struct = self._create_fee_structure(
            f"BSN Full Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )
        app = self.Application.create({
            "applicant_name": "Valid Student",
            "email": f"valid_student_{secrets.token_hex(3)}@example.com",
            "program_id": self.program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester_1.id,
            "fee_structure_id": fee_struct.id,
        })
        app.action_submit()
        app.action_approve()
        app.action_confirm()

        self.assertEqual(app.state, "confirmed")
        self.assertTrue(app.student_id)
        self.assertTrue(app.enrollment_id)
        self.assertEqual(len(app.fee_ids), 1)

        fee = app.fee_ids[0]
        self.assertEqual(fee.state, "posted")
        self.assertEqual(fee.total_amount, 500.0)
        self.assertEqual(fee.balance, 500.0)
        self.assertEqual(len(fee.line_ids), 1)
        self.assertEqual(fee.line_ids[0].name, "Tuition Fee")
        self.assertEqual(fee.line_ids[0].amount, 500.0)

    def test_07_retrying_confirmation_does_not_duplicate_invoices(self):
        """7. Retrying confirmation: duplicate invoices are not created."""
        fee_struct = self._create_fee_structure(
            f"BSN Idempotent Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )
        app = self.Application.create({
            "applicant_name": "Retry Student",
            "email": f"retry_student_{secrets.token_hex(3)}@example.com",
            "program_id": self.program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester_1.id,
            "fee_structure_id": fee_struct.id,
        })
        app.action_submit()
        app.action_approve()
        app.action_confirm()

        self.assertEqual(len(app.fee_ids), 1)
        first_fee_id = app.fee_ids[0].id

        # Calling _generate_required_fee again should not create duplicate
        fee_again = app._generate_required_fee(app.student_id)
        self.assertEqual(fee_again.id, first_fee_id)
        self.assertEqual(len(app.fee_ids), 1)

        # Retrying action_confirm on confirmed application is safe and idempotent
        app.action_confirm()
        self.assertEqual(len(app.fee_ids), 1)

    def test_08_editing_fee_structure_later_preserves_posted_invoices_and_confirmed_fee(self):
        """8. Editing a Fee Structure later: previously posted invoices remain unchanged."""
        fee_struct = self._create_fee_structure(
            f"BSN Original Fee {secrets.token_hex(3)}",
            self.program,
            self.academic_year,
            self.semester_1,
            amount=500.0,
        )
        app = self.Application.create({
            "applicant_name": "Historical Student",
            "email": f"historical_{secrets.token_hex(3)}@example.com",
            "program_id": self.program.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester_1.id,
            "fee_structure_id": fee_struct.id,
        })
        app.action_submit()
        app.action_approve()
        app.action_confirm()

        posted_fee = app.fee_ids[0]
        self.assertEqual(posted_fee.total_amount, 500.0)
        self.assertEqual(app.fee_amount, 500.0)

        # Later, an administrator updates the fee structure lines to 800.0
        fee_struct.line_ids.write({"amount": 800.0})
        self.assertEqual(fee_struct.total_amount, 800.0)

        # Recompute totals or refresh
        posted_fee.invalidate_recordset()
        app.invalidate_recordset()

        # The existing posted invoice must NOT change
        self.assertEqual(posted_fee.total_amount, 500.0)
        self.assertEqual(posted_fee.line_ids[0].amount, 500.0)

        # The confirmed admission application's displayed fee amount must NOT change
        self.assertEqual(app.fee_amount, 500.0)
