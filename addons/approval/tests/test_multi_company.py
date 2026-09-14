from freezegun import freeze_time
from psycopg.errors import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common, tagged
from odoo.tools import mute_logger

from .common import ApprovalCommon, pool_step, record_approval


class MultiCompanyCase(common.TransactionCase):
    """Two companies, each with its own manager, category, rules and one approved
    request. Shared with `approval_analytics`, whose SQL views are scoped by the
    same record rules and must be tested against the same fixture."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env["res.company"].create({"name": "Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})

        cls.manager_group = cls.env.ref("approval.group_approval_manager")

        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Manager A",
                "login": "mc_manager_a",
                "email": "mc_manager_a@test.com",
                "group_ids": [Command.link(cls.manager_group.id)],
                "company_ids": [Command.set([cls.company_a.id])],
                "company_id": cls.company_a.id,
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "Manager B",
                "login": "mc_manager_b",
                "email": "mc_manager_b@test.com",
                "group_ids": [Command.link(cls.manager_group.id)],
                "company_ids": [Command.set([cls.company_b.id])],
                "company_id": cls.company_b.id,
            }
        )
        cls.approver_b = cls.env["res.users"].create(
            {
                "name": "Approver B",
                "login": "mc_approver_b",
                "email": "mc_approver_b@test.com",
                "company_ids": [Command.set([cls.company_b.id])],
                "company_id": cls.company_b.id,
            }
        )

        cls.category_b = cls.env["approval.category"].create(
            {
                "sequence_code": "MCB01",
                "name": "Company B Category",
                "company_id": cls.company_b.id,
                "approval_minimum": 1,
                "sla_target_hours": 10,
                "step_ids": pool_step([(cls.approver_b.id, True, 10)], minimum=1),
            }
        )
        cls.rule_b = cls.env["approval.rule"].create(
            {
                "name": "Company B Rule",
                "category_id": cls.category_b.id,
                "company_id": cls.company_b.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 999999,
                "action_type": "condition",
            }
        )

        with freeze_time("2026-01-05 08:00:00"):
            cls.request_b = cls.env["approval.request"].create(
                {
                    "name": "Company B Request",
                    "request_owner_id": cls.user_b.id,
                    "category_id": cls.category_b.id,
                    "company_id": cls.company_b.id,
                    "amount": 10,
                }
            )
            cls.request_b.action_confirm()
        with freeze_time("2026-01-05 09:00:00"):
            record_approval(cls.request_b.approver_ids)
        cls.env.flush_all()


@tagged("post_install", "-at_install")
class TestMultiCompanyIsolation(MultiCompanyCase):
    def test_category_isolated_across_companies(self):
        found = (
            self.env["approval.category"]
            .with_user(self.user_a)
            .search([("id", "=", self.category_b.id)])
        )
        self.assertFalse(found, "Company A manager must not see Company B's category")
        found_b = (
            self.env["approval.category"]
            .with_user(self.user_b)
            .search([("id", "=", self.category_b.id)])
        )
        self.assertEqual(found_b, self.category_b)

    def test_rule_isolated_across_companies(self):
        found = (
            self.env["approval.rule"]
            .with_user(self.user_a)
            .search([("id", "=", self.rule_b.id)])
        )
        self.assertFalse(found, "Company A manager must not see Company B's rule")

    def test_request_and_approver_isolated_across_companies(self):
        found_request = (
            self.env["approval.request"]
            .with_user(self.user_a)
            .search([("id", "=", self.request_b.id)])
        )
        self.assertFalse(
            found_request,
            "Company A manager must not see Company B's request",
        )
        found_approver = (
            self.env["approval.approver"]
            .with_user(self.user_a)
            .search([("request_id", "=", self.request_b.id)])
        )
        self.assertFalse(
            found_approver,
            "Company A manager must not see Company B's approver rows",
        )

    def test_step_members_isolated_across_companies(self):
        domain = [("step_id.category_id", "=", self.category_b.id)]
        found = (
            self.env["approval.category.step.member"]
            .with_user(self.user_a)
            .search(domain)
        )
        self.assertFalse(
            found,
            "Company A manager must not see who approves Company B's categories",
        )
        found_b = (
            self.env["approval.category.step.member"]
            .with_user(self.user_b)
            .search(domain)
        )
        self.assertTrue(found_b)


@tagged("post_install", "-at_install")
class TestRefusalReasonMultiCompany(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_1 = cls.env["res.company"].create({"name": "Test Company 1"})
        cls.company_2 = cls.env["res.company"].create({"name": "Test Company 2"})

        cls.user_company_1 = cls.env["res.users"].create(
            {
                "name": "User Company 1",
                "login": "user_company_1",
                "email": "user1@test.com",
                "company_ids": [(6, 0, [cls.company_1.id])],
                "company_id": cls.company_1.id,
            }
        )

        cls.user_company_2 = cls.env["res.users"].create(
            {
                "name": "User Company 2",
                "login": "user_company_2",
                "email": "user2@test.com",
                "company_ids": [(6, 0, [cls.company_2.id])],
                "company_id": cls.company_2.id,
            }
        )

    def test_shared_reason_visible_to_all(self):
        shared_reason = self.env["approval.refusal.reason"].create(
            {
                "name": "Shared Reason",
                "company_id": False,
            }
        )

        reasons_c1 = (
            self.env["approval.refusal.reason"]
            .with_user(self.user_company_1)
            .search([("id", "=", shared_reason.id)])
        )
        self.assertEqual(
            len(reasons_c1), 1, "Shared reason should be visible to company 1"
        )

        reasons_c2 = (
            self.env["approval.refusal.reason"]
            .with_user(self.user_company_2)
            .search([("id", "=", shared_reason.id)])
        )
        self.assertEqual(
            len(reasons_c2), 1, "Shared reason should be visible to company 2"
        )

    def test_company_specific_reason_only_visible_to_company(self):
        reason_c1 = self.env["approval.refusal.reason"].create(
            {
                "name": "Company 1 Reason",
                "company_id": self.company_1.id,
            }
        )

        reasons_c1 = (
            self.env["approval.refusal.reason"]
            .with_user(self.user_company_1)
            .search([("id", "=", reason_c1.id)])
        )
        self.assertEqual(
            len(reasons_c1),
            1,
            "Company 1 reason should be visible to company 1 user",
        )

        reasons_c2 = (
            self.env["approval.refusal.reason"]
            .with_user(self.user_company_2)
            .search([("id", "=", reason_c1.id)])
        )
        self.assertEqual(
            len(reasons_c2),
            0,
            "Company 1 reason should NOT be visible to company 2 user",
        )


@tagged("post_install", "-at_install")
class TestMultiCompanyAuditRegressions(ApprovalCommon):
    def test_manager_cannot_see_other_companys_rule(self):
        other_company = self.env["res.company"].create(
            {"name": f"Other Co {self.id()}"},
        )
        self.approver_1.write({"company_ids": [(4, other_company.id)]})
        category = self._make_category(approvers=[self.approver_1], company_id=False)
        tier = self.env["approval.rule"].create(
            {
                "action_type": "condition",
                "operator": "between",
                "name": f"Foreign {self.id()}",
                "category_id": category.id,
                "company_id": other_company.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 0,
            },
        )
        found = (
            self.env["approval.rule"]
            .with_user(self.manager_user)
            .search(
                [("id", "=", tier.id)],
            )
        )
        self.assertFalse(
            found,
            "A tier scoped to a company the manager can't access must "
            "not be visible to them.",
        )
        with self.assertRaises((AccessError, ValidationError)):
            tier.with_user(self.manager_user).write({"threshold": 1})

    def test_category_from_other_company_not_visible(self):
        other_company = self.env["res.company"].create(
            {"name": f"Other Co {self.id()}"},
        )
        other_approver = self.env["res.users"].create(
            {
                "name": "Other Co Approver",
                "login": f"other_co_approver_{self.id()}",
                "company_id": other_company.id,
                "company_ids": [(6, 0, [other_company.id])],
            }
        )
        category = self._make_category(
            approvers=[other_approver],
            company_id=other_company.id,
        )
        found = (
            self.env["approval.category"]
            .with_user(
                self.approver_1,
            )
            .search([("id", "=", category.id)])
        )
        self.assertFalse(
            found,
            "A category scoped to another company must not be visible.",
        )

    def test_request_from_other_company_not_visible(self):
        other_company = self.env["res.company"].create(
            {"name": f"Other Co {self.id()}"},
        )
        other_user = self.env["res.users"].create(
            {
                "name": "Other Co User",
                "login": f"other_co_user_{self.id()}",
                "email": f"other_co_user_{self.id()}@test.com",
                "company_ids": [Command.link(other_company.id)],
                "company_id": other_company.id,
            },
        )
        category = self._make_category(
            approvers=[other_user],
            company_id=other_company.id,
        )
        request = (
            self.env["approval.request"]
            .with_company(
                other_company,
            )
            .create(
                {
                    "category_id": category.id,
                    "request_owner_id": other_user.id,
                    "reason": "<p>cross-company isolation test</p>",
                },
            )
        )
        self.assertEqual(request.company_id, other_company)

        found = (
            self.env["approval.request"]
            .with_user(
                self.approver_1,
            )
            .search([("id", "=", request.id)])
        )
        self.assertFalse(
            found,
            "A request scoped to another company must not be visible "
            "to a user who has no access to that company.",
        )


class TestRequestOwnerCompany(ApprovalCommon):
    def test_a_request_typed_in_belongs_to_someone_of_its_company(self):
        other = self.env["res.company"].create({"name": "Owner Elsewhere"})
        category = self._make_category(name="Owner Co", approvers=[self.approver_1])
        with self.assertRaises(ValidationError):
            self.env["approval.request"].create(
                {
                    "category_id": category.id,
                    "request_owner_id": self.owner_user.id,
                    "company_id": other.id,
                }
            )

    def test_a_document_request_may_be_owned_by_whoever_the_document_names(self):
        other = self.env["res.company"].create({"name": "Document Elsewhere"})
        self.approver_1.write({"company_ids": [(4, other.id)]})
        category = self._make_category(name="Doc Co", approvers=[self.approver_1])
        partner = self.env["res.partner"].create({"name": "Owned elsewhere"})
        request = self.env["approval.request"].create(
            {
                "category_id": category.id,
                "request_owner_id": self.owner_user.id,
                "company_id": other.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        self.assertEqual(request.company_id, other)


class TestCompanyIsNeverEmpty(ApprovalCommon):
    def test_request_without_company_is_refused(self):
        category = self._make_category(name="No Co", approvers=[self.approver_1])
        with (
            self.assertRaises((ValidationError, IntegrityError)),
            mute_logger("odoo.db.cursor"),
            self.env.cr.savepoint(),
        ):
            self.env["approval.request"].create(
                {
                    "category_id": category.id,
                    "request_owner_id": self.owner_user.id,
                    "company_id": False,
                }
            )
