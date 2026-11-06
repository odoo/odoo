from base64 import b64encode

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestUniversityPayment(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Student = self.env["university.student"]
        self.Fee = self.env["university.fee"]
        self.Payment = self.env["university.payment"]

        self.student = self.Student.create({"name": "Student A"})
        self.other_student = self.Student.create({"name": "Student B"})
        self.fee = self.Fee.create(
            {
                "student_id": self.student.id,
                "line_ids": [(0, 0, {"name": "Tuition", "amount": 100.0})],
            }
        )
        self.fee.action_post()

    def test_payment_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.Payment.create(
                {
                    "student_id": self.student.id,
                    "fee_id": self.fee.id,
                    "amount": 0.0,
                }
            )

    def test_payment_fee_must_match_student(self):
        with self.assertRaises(ValidationError):
            self.Payment.create(
                {
                    "student_id": self.other_student.id,
                    "fee_id": self.fee.id,
                    "amount": 25.0,
                }
            )

    def test_posted_payment_is_read_only(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 25.0,
            }
        )

        payment.action_post()

        with self.assertRaises(ValidationError):
            payment.write({"reference": "CHANGED"})

        with self.assertRaises(ValidationError):
            payment.write({"state": "canceled"})

    def test_payment_receipt_includes_latest_signed_signature(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 25.0,
            }
        )
        payment.action_post()
        signature = self.env["university.document.signature"].create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "signature": b64encode(b"signature-image").decode(),
                "signed_name": "Student A",
            }
        )
        signature.action_signed()

        html = self.env["ir.actions.report"]._render_qweb_html(
            "school_management.report_payment_receipt_document", payment.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html

        self.assertIn("Authorized Signature", html)
        self.assertIn("Student A", html)
        self.assertIn("data:image", html)

    def test_payment_receipt_without_signed_signature_has_no_signature_section(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 25.0,
            }
        )
        payment.action_post()

        html = self.env["ir.actions.report"]._render_qweb_html(
            "school_management.report_payment_receipt_document", payment.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html

        self.assertNotIn("Authorized Signature", html)

    def test_overpayment_blocked(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 150.0,
            }
        )
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_exact_payment_allowed(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 100.0,
            }
        )
        payment.action_post()
        self.assertEqual(payment.state, "posted")
        self.assertEqual(self.fee.state, "paid")

    def test_partial_payment_allowed(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 40.0,
            }
        )
        payment.action_post()
        self.assertEqual(payment.state, "posted")
        self.assertEqual(self.fee.state, "posted")
        self.assertEqual(self.fee.balance, 60.0)

    def test_overpayment_after_partial_allowed(self):
        first = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 40.0,
            }
        )
        first.action_post()

        second = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 60.0,
            }
        )
        second.action_post()
        self.assertEqual(self.fee.state, "paid")

    def test_overpayment_after_partial_blocked(self):
        first = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 40.0,
            }
        )
        first.action_post()

        second = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 70.0,
            }
        )
        with self.assertRaises(ValidationError):
            second.action_post()

    def test_no_overpayment_guard_for_fee_less_payment(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "amount": 500.0,
            }
        )
        payment.action_post()
        self.assertEqual(payment.state, "posted")

    def test_cancel_single_payment_reverts_fee_to_posted(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 100.0,
            }
        )
        payment.action_post()
        self.assertEqual(self.fee.state, "paid")

        payment.action_cancel()
        self.assertEqual(self.fee.state, "posted")
        self.assertEqual(self.fee.paid_amount, 0.0)
        self.assertEqual(self.fee.balance, 100.0)

    def test_cancel_one_of_two_payments_keeps_fee_posted(self):
        first = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 50.0,
            }
        )
        first.action_post()
        second = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 50.0,
            }
        )
        second.action_post()
        self.assertEqual(self.fee.state, "paid")

        first.action_cancel()
        self.assertEqual(self.fee.state, "posted")
        self.assertEqual(self.fee.paid_amount, 50.0)
        self.assertEqual(self.fee.balance, 50.0)

    def test_cancel_all_payments_reverts_fee_to_posted(self):
        first = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 50.0,
            }
        )
        first.action_post()
        second = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 50.0,
            }
        )
        second.action_post()
        self.assertEqual(self.fee.state, "paid")

        first.action_cancel()
        second.action_cancel()
        self.assertEqual(self.fee.state, "posted")
        self.assertEqual(self.fee.paid_amount, 0.0)
        self.assertEqual(self.fee.balance, 100.0)

    def test_repost_canceled_payment_restores_paid_state(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 100.0,
            }
        )
        payment.action_post()
        payment.action_cancel()
        self.assertEqual(self.fee.state, "posted")

        payment.action_post()
        self.assertEqual(self.fee.state, "paid")

    def test_payment_fully_paid_skips_email_and_logs_note_when_no_student_email(self):
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 100.0,
            }
        )
        payment.action_post()

        self.assertEqual(self.fee.state, "paid")
        notes = self.fee.message_ids
        self.assertTrue(notes)
        self.assertIn("NOT emailed", " ".join(n.body or "" for n in notes))

    def test_payment_fully_paid_sends_email_when_student_has_email(self):
        self.student.write({"email": "student@example.com"})
        payment = self.Payment.create(
            {
                "student_id": self.student.id,
                "fee_id": self.fee.id,
                "amount": 100.0,
            }
        )
        payment.action_post()

        self.assertEqual(self.fee.state, "paid")
        emails = self.env["mail.mail"].search(
            [("subject", "ilike", "Payment receipt")], order="id desc", limit=1
        )
        self.assertTrue(emails)