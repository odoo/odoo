from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import ApprovalCommon, pool_step, record_approval
from odoo.addons.approval.tests.test_multi_company import MultiCompanyCase


@tagged("post_install", "-at_install")
class TestRequestFormDefaults(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user_1 = cls.env["res.users"].create(
            {
                "name": "Test Approver 1",
                "login": "test_approver_1",
                "email": "approver1@test.com",
            }
        )
        cls.approver_user_2 = cls.env["res.users"].create(
            {
                "name": "Test Approver 2",
                "login": "test_approver_2",
                "email": "approver2@test.com",
            }
        )

    def test_copy_seeds_the_amount_from_the_owners_history(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0005",
                "name": "Smart Clone Cat",
                "has_amount": "required",
                "approval_minimum": 1,
                "step_ids": pool_step([(self.approver_user_1.id, True, 10)], minimum=1),
            }
        )
        for amt in (100, 200):
            historical = self.env["approval.request"].create(
                {
                    "name": "Hist %s" % amt,
                    "request_owner_id": self.env.user.id,
                    "category_id": category.id,
                    "amount": amt,
                }
            )
            historical.action_confirm()
            record_approval(historical.approver_ids)
        source = self.env["approval.request"].create(
            {
                "name": "source",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "amount": 1000,
            }
        )

        duplicate = source.copy()

        self.assertFalse(duplicate.name)
        self.assertEqual(duplicate.display_name, self.env._("New"))
        self.assertEqual(duplicate.amount, 150.0)
        body = " ".join(duplicate.message_ids.mapped("body"))
        self.assertIn("Duplicated from", body)
        self.assertIn(str(source.id), body)

    def test_onchange_category_autofill_copies_required_fields(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0006",
                "name": "Test Autofill Category",
                "approval_minimum": 1,
                "has_location": "required",
                "has_partner": "required",
                "has_reference": "required",
            }
        )

        partner = self.env["res.partner"].create({"name": "Test Partner"})

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Test Location",
                "partner_id": partner.id,
                "reference": "REF-123",
            }
        )

        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        record_approval(previous_request.approver_ids)

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "Test Location",
            "Location should be auto-filled from previous request",
        )
        self.assertEqual(
            new_request.partner_id,
            partner,
            "Partner should be auto-filled from previous request",
        )
        self.assertEqual(
            new_request.reference,
            "REF-123",
            "Reference should be auto-filled from previous request",
        )

    def test_onchange_category_autofill_skips_optional_fields(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0007",
                "name": "Test Optional Autofill",
                "approval_minimum": 1,
                "has_location": "optional",
                "has_partner": "required",
            }
        )

        partner = self.env["res.partner"].create({"name": "Test Partner"})

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Should Not Copy",
                "partner_id": partner.id,
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        record_approval(previous_request.approver_ids)

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Optional location should NOT be auto-filled",
        )
        self.assertEqual(
            new_request.partner_id,
            partner,
            "Required partner should be auto-filled",
        )

    def test_onchange_category_autofill_respects_existing_values(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0008",
                "name": "Test Respect Existing",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Old Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        record_approval(previous_request.approver_ids)

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
                "location": "My Custom Location",
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "My Custom Location",
            "Existing location value should NOT be overwritten by autofill",
        )

    def test_onchange_category_autofill_no_previous_request(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0009",
                "name": "Test No Previous",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        new_request = self.env["approval.request"].new(
            {
                "name": "First Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Location should be empty when no previous request",
        )

    def test_onchange_category_autofill_uses_most_recent_approved(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0010",
                "name": "Test Most Recent",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        older_request = self.env["approval.request"].create(
            {
                "name": "Older Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Older Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": older_request.id,
            }
        )
        older_request.action_confirm()
        record_approval(older_request.approver_ids)
        older_request.sudo().write({"date_confirmed": "2025-01-01 10:00:00"})

        newer_request = self.env["approval.request"].create(
            {
                "name": "Newer Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Newer Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_2.id,
                "request_id": newer_request.id,
            }
        )
        newer_request.action_confirm()
        record_approval(newer_request.approver_ids)
        newer_request.sudo().write({"date_confirmed": "2025-10-01 10:00:00"})

        new_request = self.env["approval.request"].new(
            {
                "name": "Latest Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "Newer Location",
            "Should use location from most recently approved request",
        )

    def test_onchange_category_autofill_only_current_user_requests(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0011",
                "name": "Test User Filtering",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        other_user = self.env["res.users"].create(
            {
                "name": "Other User",
                "login": "other_user",
                "email": "other@test.com",
            }
        )

        other_user_request = self.env["approval.request"].create(
            {
                "name": "Other User Request",
                "request_owner_id": other_user.id,
                "category_id": category.id,
                "location": "Other User Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": other_user_request.id,
            }
        )
        other_user_request.action_confirm()
        record_approval(other_user_request.approver_ids)

        new_request = self.env["approval.request"].new(
            {
                "name": "Current User Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Should NOT use other user's request data for autofill",
        )


@tagged("post_install", "-at_install")
class TestSmartCloneUsesTheOwnersHistory(ApprovalCommon):
    def test_duplicating_anothers_request_seeds_from_that_owners_history(self):
        category = self._make_category("Clone Cat", approvers=[self.approver_1])
        category.write({"has_amount": "optional", "has_partner": "optional"})
        owner_partner = self.env["res.partner"].create({"name": "Owner Partner"})
        other_partner = self.env["res.partner"].create({"name": "Other Partner"})

        for _ in range(3):
            request = self._prepare_request(
                category,
                amount=1000.0,
                partner_id=owner_partner.id,
            )
            request.with_user(self.approver_1).action_approve()
        for _ in range(3):
            request = self._prepare_request(
                category,
                owner=self.manager_user,
                amount=7.0,
                partner_id=other_partner.id,
            )
            request.with_user(self.approver_1).action_approve()

        source = self._prepare_request(
            category,
            confirm=False,
            amount=1000.0,
            partner_id=owner_partner.id,
        )
        clone = source.with_user(self.manager_user).copy()

        self.assertEqual(clone.request_owner_id, self.owner_user)
        self.assertAlmostEqual(clone.amount, 1000.0, places=2)
        self.assertEqual(clone.partner_id, owner_partner)

    def test_the_history_lookup_is_bounded(self):
        category = self._make_category("Bounded Cat", approvers=[self.approver_1])
        for index in range(40):
            request = self._prepare_request(category, amount=100.0 + index)
            request.with_user(self.approver_1).action_approve()
        request = self._prepare_request(category, confirm=False)

        loaded = []
        Request = type(self.env["approval.request"])
        original = Request.search

        def spy(records, domain, *args, **kwargs):
            result = original(records, domain, *args, **kwargs)
            if "'approved'" in repr(domain):
                loaded.append(len(result))
            return result

        self.patch(Request, "search", spy)
        recent = request._recent_approved_by_owner(limit=10)

        self.assertEqual(len(recent), 10)
        self.assertTrue(loaded)
        self.assertLessEqual(
            loaded[0],
            10,
            "the lookup keeps 10 rows for one category but loaded %s" % loaded[0],
        )


@tagged("post_install", "-at_install")
class TestDocumentRequirementLanguage(ApprovalCommon):
    def _install_spanish(self):
        lang = (
            self.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "es_MX")], limit=1)
        )
        if not lang:
            self.skipTest("es_MX language not available in this database")
        lang.active = True

    def test_a_spanish_deployment_never_has_to_rename_a_file(self):
        self._install_spanish()
        category = self._make_category(
            "Doc Language",
            approvers=[(self.approver_1, True, 10)],
            has_document="required",
        )
        requirement = self.env["approval.document.requirement"].create(
            {"category_id": category.id, "name": "Invoice", "required": True},
        )
        requirement.with_context(lang="es_MX").name = "Factura"

        request = self._prepare_request(category, confirm=False)
        self.env["ir.attachment"].create(
            {
                "name": "escaneo-0001.pdf",
                "res_model": "approval.request",
                "res_id": request.id,
                "raw": b"real document",
                "approval_requirement_id": requirement.id,
            },
        )
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_two_requirements_may_now_share_a_translation(self):
        self._install_spanish()
        category = self._make_category(
            "Doc Collision",
            approvers=[(self.approver_1, True, 10)],
            has_document="required",
        )
        first = self.env["approval.document.requirement"].create(
            {"category_id": category.id, "name": "Invoice", "required": True},
        )
        second = self.env["approval.document.requirement"].create(
            {"category_id": category.id, "name": "Receipt", "required": True},
        )
        first.with_context(lang="es_MX").name = "Factura"
        second.with_context(lang="es_MX").name = "Factura"

        request = self._prepare_request(category, confirm=False)
        for requirement in (first, second):
            self.env["ir.attachment"].create(
                {
                    "name": "doc-%d.pdf" % requirement.id,
                    "res_model": "approval.request",
                    "res_id": request.id,
                    "raw": b"real document",
                    "approval_requirement_id": requirement.id,
                },
            )
        request.action_confirm()
        self.assertEqual(request.state, "pending")


@tagged("post_install", "-at_install")
class TestRequestTemplates(ApprovalCommon):
    def _category(self):
        return self._make_category(
            name=f"Template Cat {self.id()}",
            approvers=[self.approver_1],
        )

    def test_template_creates_prefilled_request_action(self):
        category = self._category()
        template = self.env["approval.template"].create(
            {
                "name": "Weekly",
                "category_id": category.id,
                "default_priority": "2",
            }
        )
        self.assertEqual(template.usage_count, 0)
        action = template.action_create_request()
        self.assertEqual(action["res_model"], "approval.request")
        self.assertEqual(action["context"]["default_category_id"], category.id)
        self.assertEqual(action["context"]["default_template_id"], template.id)
        self.assertEqual(action["context"]["default_priority"], "2")


@tagged("post_install", "-at_install")
class TestFormFieldsLock(ApprovalCommon):
    def test_form_fields_freeze_once_sent_and_reopen_in_draft(self):
        category = self._make_category(
            name=f"Form Lock {self.id()}",
            approvers=[self.approver_1],
        )
        draft = self._prepare_request(category, confirm=False)
        draft.with_user(self.owner_user).write(
            {"reference": "draft-ref", "location": "here"}
        )
        self.assertEqual(draft.reference, "draft-ref")

        draft.action_confirm()
        for field, value in {"reference": "new-ref", "location": "elsewhere"}.items():
            with self.assertRaises(
                ValidationError, msg=f"{field} must be frozen after send"
            ):
                draft.with_user(self.owner_user).write({field: value})


@tagged("post_install", "-at_install")
class TestTemplateMultiCompany(MultiCompanyCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_b = cls.env["approval.template"].create(
            {
                "name": "Company B Template",
                "category_id": cls.category_b.id,
                "company_id": cls.company_b.id,
            }
        )

    def test_template_isolated_across_companies(self):
        found = (
            self.env["approval.template"]
            .with_user(self.user_a)
            .search([("id", "=", self.template_b.id)])
        )
        self.assertFalse(found, "Company A manager must not see Company B's template")
