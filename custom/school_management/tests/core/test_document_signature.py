from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestDocumentSignature(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Student = self.env["university.student"]
        self.Fee = self.env["university.fee"]
        self.Signature = self.env["university.document.signature"]

        self.student = self.Student.create({"name": "Student A"})
        self.other_student = self.Student.create({"name": "Student B"})
        self.fee = self.Fee.create(
            {
                "student_id": self.student.id,
                "line_ids": [(0, 0, {"name": "Tuition", "amount": 100.0})],
            }
        )
        self.fee.action_post()

    def test_valid_signature_creation_generates_reference(self):
        signature = self.Signature.create(
            {"student_id": self.student.id, "fee_id": self.fee.id}
        )

        self.assertTrue(signature.name.startswith("SIGN-"))
        self.assertEqual(signature.state, "pending")

    def test_fee_student_mismatch_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.Signature.create(
                {"student_id": self.other_student.id, "fee_id": self.fee.id}
            )

    def test_request_signature_creates_and_reuses_pending_record(self):
        first_action = self.fee.action_request_signature()
        signature = self.Signature.browse(first_action["res_id"])

        self.assertTrue(signature.exists())
        self.assertEqual(signature.state, "pending")
        self.assertEqual(signature.student_id, self.student)
        self.assertEqual(signature.fee_id, self.fee)

        second_action = self.fee.action_request_signature()
        self.assertEqual(second_action["res_id"], signature.id)
        self.assertEqual(self.fee.signature_count, 1)

    def test_signed_signature_is_protected_from_editing(self):
        signature = self.Signature.create(
            {"student_id": self.student.id, "fee_id": self.fee.id}
        )
        signature.action_signed()

        for vals in (
            {"signature": b"signed"},
            {"signed_name": "Changed"},
            {"student_id": self.other_student.id},
            {"fee_id": self.Fee.create({"student_id": self.student.id}).id},
            {"name": "CHANGED"},
        ):
            with self.assertRaises(UserError):
                signature.write(vals)

        signature.write({"state": "signed", "signed_on": fields.Datetime.now()})

    def test_student_user_can_read_own_fee_without_signature_access(self):
        user = self.env["res.users"].create(
            {
                "name": "Fee Student Portal User",
                "login": "fee_student_access_test",
                "group_ids": [
                    (
                        6,
                        0,
                        [self.env.ref("school_management.group_school_student").id],
                    )
                ],
            }
        )
        self.student.write({"user_id": user.id})

        self.Signature.create({"student_id": self.student.id, "fee_id": self.fee.id})

        fee_fields = [
            "name",
            "student_id",
            "academic_year_id",
            "semester_id",
            "date",
            "due_date",
            "currency_id",
            "line_ids",
            "payment_ids",
            "total_amount",
            "paid_amount",
            "balance",
            "state",
        ]
        result = self.fee.with_user(user).read(fee_fields)[0]
        self.assertEqual(result["name"], self.fee.name)
        self.assertEqual(len(result["line_ids"]), 1)

        with self.assertRaises(AccessError):
            self.fee.with_user(user).read(["signature_ids"])
