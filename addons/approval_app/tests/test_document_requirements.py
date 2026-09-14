import base64

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import (
    ApprovalCommon,
    add_category_approver,
    new_trip_category,
)


@tagged("post_install", "-at_install")
class TestDocumentRequirements(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Doc Approver",
                "login": "doc_approver",
                "email": "doc_approver@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "has_document": "required",
            }
        )
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Doc Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
            "location": "testland",
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def _requirement(self, name, required=True, category=None):
        return self.env["approval.document.requirement"].create(
            {
                "name": name,
                "category_id": (category or self.category).id,
                "required": required,
            },
        )

    def _attach_file(self, request, filename="test.pdf", requirement=None):
        return self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_model": "approval.request",
                "res_id": request.id,
                "datas": base64.b64encode(b"test content"),
                "approval_requirement_id": requirement.id if requirement else False,
            }
        )

    def test_required_document_blocks_without_attachment(self):
        request = self._create_request()
        with self.assertRaises(UserError):
            request.action_confirm()

    def test_required_document_allows_with_attachment(self):
        request = self._create_request()
        self._attach_file(request)
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_typed_requirement_blocks_when_nothing_is_linked_to_it(self):
        invoice = self._requirement("Invoice")
        request = self._create_request()
        self._attach_file(request, filename="random_photo.jpg")
        with self.assertRaises(UserError) as caught:
            request.action_confirm()
        self.assertIn(invoice.name, str(caught.exception))

    def test_typed_requirement_passes_when_a_file_is_linked_to_it(self):
        invoice = self._requirement("Invoice")
        request = self._create_request()
        self._attach_file(request, filename="scan001.pdf", requirement=invoice)
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_the_file_name_no_longer_means_anything(self):
        invoice = self._requirement("Invoice")
        named = self._create_request()
        self._attach_file(named, filename="Invoice_March_2026.pdf")
        with self.assertRaises(UserError):
            named.action_confirm()

        unnamed = self._create_request()
        self._attach_file(unnamed, filename="scan001.pdf", requirement=invoice)
        unnamed.action_confirm()
        self.assertEqual(unnamed.state, "pending")

    def test_one_file_cannot_satisfy_two_requirements(self):
        invoice = self._requirement("Invoice")
        self._requirement("Contract")
        request = self._create_request()
        self._attach_file(
            request,
            filename="invoice-and-contract-combined.pdf",
            requirement=invoice,
        )
        with self.assertRaises(UserError) as caught:
            request.action_confirm()
        self.assertIn("Contract", str(caught.exception))

    def test_multiple_requirements_all_must_be_linked(self):
        invoice = self._requirement("Invoice")
        quote = self._requirement("Quote")
        request = self._create_request()
        self._attach_file(request, filename="a.pdf", requirement=invoice)
        with self.assertRaises(UserError):
            request.action_confirm()

        self._attach_file(request, filename="b.pdf", requirement=quote)
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_optional_requirement_does_not_block(self):
        invoice = self._requirement("Invoice")
        self._requirement("Photo", required=False)
        request = self._create_request()
        self._attach_file(request, filename="a.pdf", requirement=invoice)
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_no_requirements_only_checks_basic(self):
        request = self._create_request()
        self._attach_file(request, filename="anything.pdf")
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_optional_document_category_skips_requirements(self):
        self.category.has_document = "optional"
        self._requirement("Invoice")
        request = self._create_request()
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_a_requirement_of_another_category_cannot_be_claimed(self):
        other_category = self.env["approval.category"].create(
            {"name": "Other Doc Cat", "sequence_code": "DOCOTH"},
        )
        foreign = self._requirement("Invoice", category=other_category)
        request = self._create_request()
        with self.assertRaises(ValidationError):
            self._attach_file(request, filename="a.pdf", requirement=foreign)

    def test_the_link_needs_an_approval_request_behind_it(self):
        invoice = self._requirement("Invoice")
        with self.assertRaises(ValidationError):
            self.env["ir.attachment"].create(
                {
                    "name": "loose.pdf",
                    "datas": base64.b64encode(b"x"),
                    "approval_requirement_id": invoice.id,
                },
            )


@tagged("post_install", "-at_install")
class TestDocumentRequirementsAuditRegressions(ApprovalCommon):
    def test_document_requirements_still_blocks_genuinely_missing(self):
        category = self._make_category(
            approvers=[self.approver_1],
            has_document="required",
        )
        invoice = self.env["approval.document.requirement"].create(
            {"category_id": category.id, "name": "invoice", "required": True},
        )
        self.env["approval.document.requirement"].create(
            {"category_id": category.id, "name": "contract", "required": True},
        )
        request = self._prepare_request(category, confirm=False)
        self.env["ir.attachment"].create(
            {
                "name": "invoice_only.pdf",
                "res_model": "approval.request",
                "res_id": request.id,
                "datas": base64.b64encode(b"test content"),
                "approval_requirement_id": invoice.id,
            },
        )
        with self.assertRaises(UserError):
            request.action_confirm()
