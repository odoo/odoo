from psycopg import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


class TestCompany(TransactionCase):
    def test_code_builds_complete_name(self):
        company = self.env["res.company"].create(
            {"name": "Test Company", "code": "TEST"}
        )
        self.assertEqual(company.complete_name, "TEST - Test Company")
        company.code = False
        self.assertEqual(company.complete_name, "Test Company")

    def test_display_name_prefers_code(self):
        company = self.env["res.company"].create(
            {"name": "Test Company", "code": "TEST"}
        )
        self.assertEqual(company.display_name, "TEST")
        company.code = False
        self.assertEqual(company.display_name, "Test Company")

    def test_display_name_searches_code_and_name(self):
        company = self.env["res.company"].create(
            {"name": "Test Company", "code": "TEST"}
        )
        self.assertIn(company.id, [c[0] for c in company.name_search("Test Company")])
        self.assertIn(company.id, [c[0] for c in company.name_search("TEST")])

    def test_code_is_normalised(self):
        company = self.env["res.company"].create(
            {"name": "Test Company", "code": "  ab "}
        )
        self.assertEqual(company.code, "AB")
        company.write({"code": " cd"})
        self.assertEqual(company.code, "CD")
        company.write({"code": "   "})
        self.assertFalse(company.code)

    def test_normalize_vals_does_not_mutate_caller_dict(self):
        create_vals = {"name": "Audit Caller", "code": "  ac "}
        create_vals_copy = dict(create_vals)
        company = self.env["res.company"].create(create_vals)
        self.assertEqual(create_vals, create_vals_copy)
        self.assertEqual(company.code, "AC")

        write_vals = {"code": " dd "}
        write_vals_copy = dict(write_vals)
        company.write(write_vals)
        self.assertEqual(write_vals, write_vals_copy)
        self.assertEqual(company.code, "DD")

    def test_code_may_be_unset_on_several_companies(self):
        first = self.env["res.company"].create({"name": "No Code One"})
        second = self.env["res.company"].create({"name": "No Code Two"})
        (first + second).flush_recordset()
        self.assertFalse(first.code)
        self.assertFalse(second.code)
        self.assertEqual(first.display_name, "No Code One")

    def test_code_is_unique(self):
        self.env["res.company"].create({"name": "First", "code": "DUP"})
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["res.company"].create({"name": "Second", "code": "dup"})

    def test_check_active(self):
        company = self.env["res.company"].create({"name": "foo"})
        user = self.env["res.users"].create(
            {
                "name": "foo",
                "login": "foo",
                "company_id": company.id,
                "company_ids": company.ids,
            }
        )

        with self.assertRaisesRegex(ValidationError, r"cannot be archived[\s\S]*foo"):
            company.action_archive()

        user.action_archive()
        company.action_archive()

        with self.assertRaisesRegex(
            ValidationError, "Company foo is not in the allowed companies"
        ):
            user.action_unarchive()

        main_company = self.env.ref("base.main_company")
        user.write(
            {
                "company_id": main_company.id,
                "company_ids": main_company.ids,
            }
        )
        user.action_unarchive()

    def test_check_active_aggregates_all_offending_companies(self):
        company_a, company_b = self.env["res.company"].create(
            [{"name": "arch co A"}, {"name": "arch co B"}]
        )
        for i, company in enumerate((company_a, company_b)):
            self.env["res.users"].create(
                {
                    "name": f"arch user {i}",
                    "login": f"arch_user_{i}",
                    "company_id": company.id,
                    "company_ids": company.ids,
                }
            )
        with self.assertRaises(ValidationError) as capture:
            (company_a + company_b).action_archive()
        message = str(capture.exception)
        self.assertIn("arch co A", message)
        self.assertIn("arch co B", message)

    def test_logo_check(self):
        company = self.env["res.company"].create({"name": "foo"})

        self.assertTrue(company.image_1920, "Should have a default logo")
        self.assertTrue(company.uses_default_logo)
        company.partner_id.image_1920 = False
        self.assertTrue(company.uses_default_logo)
        company.partner_id.image_1920 = (
            "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        )
        self.assertFalse(company.uses_default_logo)

    def test_create_branch_with_default_parent_id(self):
        branch = (
            self.env["res.company"]
            .with_context(default_parent_id=self.env.company.id)
            .create({"name": "Branch Company"})
        )
        self.assertFalse(branch.partner_id.parent_id)

    def test_color_is_the_party_color(self):
        company = self.env["res.company"].create({"name": "color root"})
        company.partner_id.color = 5
        self.assertEqual(company.color, 5)
        company.color = 7
        self.assertEqual(company.partner_id.color, 7)

    def test_company_partner_ids_cache_invalidation(self):
        Company = self.env["res.company"]
        company = Company.create({"name": "cache co"})
        self.assertIn(company.partner_id.id, Company._get_company_partner_ids())

        new_partner = self.env["res.partner"].create(
            {"name": "new company partner", "is_company": True}
        )
        company.write({"partner_id": new_partner.id})
        self.assertIn(
            new_partner.id,
            Company._get_company_partner_ids(),
            "partner_id writes must invalidate the company partner ids cache",
        )

    def test_address_is_the_partner_address_in_both_directions(self):
        company = self.env["res.company"].create({"name": "address co"})
        company.partner_id.write({"street": "1 Partner St", "city": "Partnerville"})
        self.assertEqual(company.street, "1 Partner St")
        self.assertEqual(company.city, "Partnerville")
        company.write({"street": "2 Company St", "zip": "9000"})
        self.assertEqual(company.partner_id.street, "2 Company St")
        self.assertEqual(company.partner_id.zip, "9000")

    def test_accessible_branches_is_scoped_to_the_branch_and_the_allowed_companies(
        self,
    ):
        Company = self.env["res.company"]
        root = Company.create({"name": "branch root"})
        child = Company.create({"name": "branch child", "parent_id": root.id})
        grand = Company.create({"name": "branch grand", "parent_id": child.id})
        user = new_test_user(
            self.env,
            "branch_reader",
            company_id=root.id,
            company_ids=[Command.set((root + child + grand).ids)],
        )

        def branches(company, allowed):
            return (
                company.with_user(user)
                .with_context(allowed_company_ids=allowed.ids)
                ._get_accessible_branches()
            )

        self.assertEqual(branches(root, root + child + grand), root + child + grand)
        self.assertEqual(branches(child, root + child + grand), child + grand)
        self.assertEqual(branches(root, grand), grand)
        self.assertEqual(branches(root, root + child), root + child)

    def test_the_companies_of_an_environment_begin_with_its_company(self):
        user = new_test_user(self.env, "companies-first")
        own = user.company_id
        earlier = self.env["res.company"].create(
            {"name": "AAA sorts first", "sequence": -1}
        )
        user.write({"company_ids": [Command.link(earlier.id)]})
        env = self.env(user=user, context={})
        self.assertEqual(env.company, own)
        self.assertEqual(env.companies[:1], env.company)
        self.assertEqual(set(env.companies.ids), {own.id, earlier.id})
        self.assertEqual(
            self.env(
                user=user, context={"allowed_company_ids": [earlier.id, own.id]}
            ).companies.ids,
            [earlier.id, own.id],
            "a list the request sends keeps its own order",
        )

    def test_get_main_company_falls_back_to_the_first_company(self):
        main = self.env.ref("base.main_company")
        self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "main_company")]
        ).unlink()
        self.env.registry.clear_cache()
        self.assertFalse(self.env.ref("base.main_company", raise_if_not_found=False))
        self.assertEqual(self.env["res.company"]._get_main_company(), main)

    def test_company_name_is_unique_through_the_party(self):
        company = self.env["res.company"].create({"name": "unique co"})
        with self.assertRaises(ValidationError):
            self.env["res.company"].create({"name": "unique co"})
        with self.assertRaises(ValidationError):
            self.env["res.company"].create(
                {"name": "twin co"}
            ).partner_id.name = "unique co"
        other = self.env["res.partner"].create({"name": "unique co"})
        self.assertTrue(other, "a plain contact may share a company's name")
        company.name = "renamed co"
        self.assertEqual(company.partner_id.name, "renamed co")

    def test_identity_is_readable_by_whoever_reads_the_company(self):
        company = self.env["res.company"].create(
            {"name": "public identity co", "email": "co@example.com"}
        )
        company.partner_id.comment = "private note"
        portal = new_test_user(
            self.env,
            login="af_portal",
            groups="base.group_portal",
            company_ids=[Command.set([self.env.company.id, company.id])],
        )
        as_portal = company.with_user(portal).with_context(
            allowed_company_ids=company.ids
        )
        with self.assertRaises(AccessError):
            company.partner_id.with_user(portal).name
        self.assertIn(
            company,
            self.env["res.company"]
            .with_user(portal)
            .with_context(allowed_company_ids=company.ids)
            .search([("id", "=", company.id)]),
        )
        self.assertEqual(as_portal.name, "public identity co")
        self.assertEqual(as_portal.email, "co@example.com")
        self.assertTrue(as_portal.image_1920)
        with self.assertRaises(AccessError):
            as_portal.comment

    def test_identity_comes_with_the_company_row(self):
        company = self.env["res.company"].create({"name": "one row co"})
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertQueryCount(1):
            self.assertEqual(company.name, "one row co")
            self.assertEqual(company.email, False)

    def test_identity_is_written_by_whoever_writes_the_company(self):
        company = self.env["res.company"].create({"name": "writable identity co"})
        manager = new_test_user(
            self.env,
            login="af_erp_manager",
            groups="base.group_erp_manager",
            company_ids=[Command.set([self.env.company.id, company.id])],
        )
        self.assertFalse(manager.has_group("base.group_partner_manager"))
        as_manager = company.with_user(manager)
        as_manager.write({"name": "renamed identity co", "email": "co@example.com"})
        self.assertEqual(company.partner_id.name, "renamed identity co")
        self.assertEqual(company.partner_id.email, "co@example.com")
        with self.assertRaises(AccessError):
            as_manager.partner_id.write({"comment": "not identity"})
        with self.assertRaises(AccessError):
            as_manager.write({"bank_ids": [Command.create({"acc_number": "X-1"})]})
        with self.assertRaises(AccessError):
            as_manager.write({"phone_ids": [Command.create({"number": "+1 555 0100"})]})
        self.assertFalse(company.partner_id.bank_ids)
        employee = new_test_user(
            self.env,
            login="af_employee",
            groups="base.group_user",
            company_ids=[Command.set([self.env.company.id, company.id])],
        )
        with self.assertRaises(AccessError):
            company.with_user(employee).write({"name": "not allowed"})

    def test_company_partner_has_no_contact_parent(self):
        company = (
            self.env["res.company"]
            .with_context(default_parent_id=self.env.company.id)
            .create({"name": "branch via context"})
        )
        self.assertEqual(company.parent_id, self.env.company)
        self.assertFalse(company.partner_id.parent_id)
        self.assertTrue(company.partner_id.is_company)


@tagged("post_install", "-at_install")
class TestCompanyRootSearch(TransactionCase):
    def test_root_id_search_returns_the_root_and_its_descendants(self):
        Company = self.env["res.company"]
        root = Company.create({"name": "Root Co"})
        child = Company.create({"name": "Child Co", "parent_id": root.id})
        grandchild = Company.create({"name": "Grandchild Co", "parent_id": child.id})
        other = Company.create({"name": "Other Co"})
        self.assertEqual(grandchild.root_id, root)
        self.assertEqual(
            Company.search([("root_id", "in", root.ids)]), root | child | grandchild
        )
        self.assertFalse(
            Company.search([("root_id", "in", child.ids)]),
            "a branch is nobody's root",
        )
        self.assertIn(other, Company.search([("root_id", "not in", root.ids)]))
        self.assertNotIn(child, Company.search([("root_id", "not in", root.ids)]))


@tagged("post_install", "-at_install")
class TestCompanyPublicUser(TransactionCase):
    def test_get_public_user_creates_one_per_company(self):
        company = self.env["res.company"].create({"name": "Public Co"})
        public_user = company._get_public_user()
        self.assertTrue(public_user)
        self.assertEqual(public_user.company_id, company)
        self.assertEqual(public_user.login, f"public-user@company-{company.id}.com")

    def test_get_public_user_is_idempotent(self):
        company = self.env["res.company"].create({"name": "Public Co 2"})
        first = company._get_public_user()
        second = company._get_public_user()
        self.assertEqual(first, second)

    def test_get_public_user_found_without_group_public_membership(self):
        company = self.env["res.company"].create({"name": "Public Co 3"})
        public_user = company._get_public_user()
        public_group = self.env.ref("base.group_public")
        public_user.sudo().write({"group_ids": [Command.unlink(public_group.id)]})
        self.assertNotIn(public_user, public_group.sudo().all_user_ids)

        again = company._get_public_user()
        self.assertEqual(
            again,
            public_user,
            "The public user must be found by its per-company login even when "
            "it is not a member of base.group_public (RC-L3).",
        )


@tagged("post_install", "-at_install")
class TestCompanyMembershipCache(TransactionCase):
    def test_company_side_user_ids_write_invalidates_user_company_cache(self):
        user = self.env["res.users"].create(
            {
                "name": "Membership Probe",
                "login": "membership_probe",
                "company_ids": [Command.set(self.env.company.ids)],
                "company_id": self.env.company.id,
            }
        )
        other = self.env["res.company"].create({"name": "Extra Co"})
        other.write({"user_ids": [Command.link(user.id)]})
        self.assertIn(
            other.id,
            user._get_company_ids(),
            "linking a user from the company side must refresh _get_company_ids",
        )
        other.write({"user_ids": [Command.unlink(user.id)]})
        self.assertNotIn(
            other.id,
            user._get_company_ids(),
            "unlinking a user from the company side must refresh _get_company_ids",
        )
