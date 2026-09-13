import unittest
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


class TestMergePartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.Bank = self.env["res.partner.bank"]

        self.partner1 = self.Partner.create(
            {"name": "Partner 1", "email": "partner1@example.com"}
        )
        self.partner2 = self.Partner.create(
            {"name": "Partner 2", "email": "partner2@example.com"}
        )
        self.partner3 = self.Partner.create(
            {"name": "Partner 3", "email": "partner3@example.com"}
        )

        self.bank1 = self.Bank.create(
            {"acc_number": "12345", "partner_id": self.partner1.id}
        )
        self.bank2 = self.Bank.create(
            {"acc_number": "54321", "partner_id": self.partner2.id}
        )
        self.bank3 = self.Bank.create(
            {"acc_number": "12345", "partner_id": self.partner3.id}
        )

        self.attachment1 = self.env["ir.attachment"].create(
            {
                "name": "Attachment 1",
                "res_model": "res.partner",
                "res_id": self.partner1.id,
            }
        )
        self.attachment2 = self.env["ir.attachment"].create(
            {
                "name": "Attachment 2",
                "res_model": "res.partner",
                "res_id": self.partner2.id,
            }
        )
        self.attachment_bank1 = self.env["ir.attachment"].create(
            {
                "name": "Attachment Bank 1",
                "res_model": "res.partner.bank",
                "res_id": self.bank1.id,
            }
        )
        self.attachment_bank2 = self.env["ir.attachment"].create(
            {
                "name": "Attachment Bank 2",
                "res_model": "res.partner.bank",
                "res_id": self.bank2.id,
            }
        )
        self.attachment_bank3 = self.env["ir.attachment"].create(
            {
                "name": "Attachment Bank 2",
                "res_model": "res.partner.bank",
                "res_id": self.bank3.id,
            }
        )

    def test_merge_parent_with_child_is_rejected(self):
        parent = self.Partner.create(
            {"name": "Parent Co", "email": "parent@example.com"}
        )
        child = self.Partner.create(
            {"name": "Child Co", "email": "child@example.com", "parent_id": parent.id}
        )
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        with self.assertRaises(UserError):
            wizard._merge([parent.id, child.id])
        self.assertTrue(parent.exists() and child.exists())
        self.assertNotEqual(parent.parent_id, parent)
        self.assertNotEqual(child.parent_id, child)

    def test_merge_partners_without_bank_accounts(self):
        partner4 = self.Partner.create(
            {"name": "Partner 4", "email": "partner4@example.com"}
        )
        partner5 = self.Partner.create(
            {"name": "Partner 5", "email": "partner5@example.com"}
        )
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge([partner4.id, partner5.id], partner4)
        self.assertFalse(
            partner5.exists(), "Source partner should be deleted after merge"
        )
        self.assertTrue(
            partner4.exists(), "Destination partner should exist after merge"
        )

    def test_merge_partners_with_unique_bank_accounts(self):
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(
            self.partner2.exists(),
            "Source partner should be deleted after merge",
        )
        self.assertTrue(
            self.partner1.exists(),
            "Destination partner should exist after merge",
        )
        self.assertEqual(
            self.bank1.partner_id,
            self.partner1,
            "Bank account should belong to destination partner",
        )
        self.assertEqual(
            self.bank2.partner_id,
            self.partner1,
            "Bank account should be reassigned to destination partner",
        )

    def test_merge_partners_with_duplicate_bank_accounts(self):
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        src_partners = self.partner1 + self.partner3
        wizard._merge((src_partners + self.partner2).ids, self.partner2)

        self.assertFalse(
            src_partners.exists(),
            "Source partners should be deleted after merge",
        )
        self.assertTrue(
            self.partner2.exists(),
            "Destination partner should exist after merge",
        )
        self.assertRecordValues(
            self.partner2.bank_ids,
            [
                {"acc_number": "12345"},
                {"acc_number": "54321"},
            ],
        )
        self.assertEqual(
            self.attachment_bank1.res_id,
            self.bank1.id,
            "Bank attachment should remain linked to the correct bank account",
        )
        self.assertEqual(
            self.attachment_bank3.res_id,
            self.bank1.id,
            "Bank attachment should be reassigned to the correct bank account",
        )

    def test_merge_partners_with_duplicate_bank_accounts_with_destination(self):
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge([self.partner1.id, self.partner3.id], self.partner1)

        self.assertFalse(
            self.partner3.exists(),
            "Source partner should be deleted after merge",
        )
        self.assertTrue(
            self.partner1.exists(),
            "Destination partner should exist after merge",
        )
        self.assertEqual(
            len(self.partner1.bank_ids),
            1,
            "There should be a single bank account after merge",
        )
        self.assertIn(
            self.bank1,
            self.partner1.bank_ids,
            "The original bank account of the destination partner should remain",
        )
        self.assertFalse(
            self.bank3.exists(),
            "The duplicate bank account should have been deleted.",
        )

    def test_merge_partners_with_references(self):
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(
            self.partner2.exists(),
            "Source partner should be deleted after merge",
        )
        self.assertTrue(
            self.partner1.exists(),
            "Destination partner should exist after merge",
        )
        self.assertEqual(
            self.attachment1.res_id,
            self.partner1.id,
            "Attachment should be linked to the destination partner",
        )
        self.assertEqual(
            self.attachment2.res_id,
            self.partner1.id,
            "Attachment should be reassigned to the destination partner",
        )

    def test_merge_partners_with_peon_user(self):
        self.env["ir.model.access"].create(
            {
                "name": "peon.access.merge.wizard",
                "group_id": self.env.ref("base.group_user").id,
                "model_id": self.env.ref(
                    "base.model_base_partner_merge_automatic_wizard"
                ).id,
                "perm_read": 1,
                "perm_write": 1,
                "perm_create": 1,
            }
        )
        self.env["ir.model.access"].create(
            {
                "name": "peon.access.merge.wizard.line",
                "group_id": self.env.ref("base.group_user").id,
                "model_id": self.env.ref("base.model_base_partner_merge_line").id,
                "perm_read": 1,
                "perm_write": 1,
                "perm_create": 1,
            }
        )
        partner_peon = self.env["res.partner"].create(
            {
                "name": "Peon",
                "email": "mark.peon@example.com",
            }
        )
        user_peon = self.env["res.users"].create(
            {
                "login": "peon",
                "password": "peon",
                "partner_id": partner_peon.id,
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )

        with self.assertRaises(AccessError):
            self.bank1.with_user(user_peon).partner_id = self.partner2

        wizard = (
            self.env["base.partner.merge.automatic.wizard"]
            .with_user(user_peon)
            .create({})
        )
        src_partners = self.partner1 + self.partner3
        wizard._merge(
            (src_partners + self.partner2).ids,
            self.partner2,
            extra_checks=False,
        )

        self.assertFalse(
            src_partners.exists(),
            "Source partners should be deleted after merge",
        )
        self.assertTrue(
            self.partner2.exists(),
            "Destination partner should exist after merge",
        )
        self.assertRecordValues(
            self.partner2.bank_ids,
            [
                {"acc_number": "12345"},
                {"acc_number": "54321"},
            ],
        )
        self.assertEqual(
            self.attachment_bank1.res_id,
            self.bank1.id,
            "Bank attachment should remain linked to the correct bank account",
        )
        self.assertEqual(
            self.attachment_bank3.res_id,
            self.bank1.id,
            "Bank attachment should be reassigned to the correct bank account",
        )

    def test_merge_aligns_user_company_to_destination(self):
        Company = self.env["res.company"]
        company_a, company_b = Company.create(
            [{"name": "Merge A"}, {"name": "Merge B"}]
        )
        src = self.Partner.create(
            {"name": "merge src", "email": "m@example.com", "company_id": company_a.id}
        )
        dst = self.Partner.create(
            {"name": "merge dst", "email": "m@example.com", "company_id": company_b.id}
        )
        user = self.env["res.users"].create(
            {
                "login": "merge_company_user",
                "partner_id": src.id,
                "company_id": company_a.id,
                "company_ids": [Command.set([company_a.id, company_b.id])],
            }
        )
        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.assertEqual(user.company_id, company_b)
        self.assertIn(company_b, user.company_ids)


@tagged("post_install", "-at_install")
class TestMergePartnerForeignKeyClash(TransactionCase):
    """What a merge does with two sources, one of which repeats an account.

    This asserts the outcome rather than the mechanism on purpose. It used to
    call `_update_foreign_keys_generic` directly and rely on that pass dropping
    the redundant row, which worked only while `partner_id` sat in the account
    number's unique key. It no longer does -- the number is unique per company
    -- so `_merge_bank_accounts` is what resolves a repeat, and the merge is
    what has to be exercised for the answer to mean anything.
    """

    def test_a_repeated_account_is_dropped_and_the_others_are_carried_over(self):
        Partner = self.env["res.partner"]
        Bank = self.env["res.partner.bank"]
        dst = Partner.create({"name": "fk dst", "email": "fk@example.com"})
        src_clash = Partner.create({"name": "fk src clash", "email": "fk@example.com"})
        src_keep = Partner.create({"name": "fk src keep", "email": "fk@example.com"})

        Bank.create({"acc_number": "CLASH", "partner_id": dst.id})
        bank_clash = Bank.create({"acc_number": "CLASH", "partner_id": src_clash.id})
        bank_keep = Bank.create({"acc_number": "UNIQUE-B", "partner_id": src_keep.id})

        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge((dst + src_clash + src_keep).ids, dst)
        self.env.invalidate_all()

        self.assertTrue(
            bank_keep.exists(),
            "the account the destination does not hold must survive the merge",
        )
        self.assertEqual(
            bank_keep.partner_id,
            dst,
            "the account the destination does not hold must be carried over to it",
        )
        self.assertFalse(
            bank_clash.exists(),
            "only the account the destination already holds is dropped",
        )


@tagged("post_install", "-at_install")
class TestMergePartnerCompanyDependent(TransactionCase):
    def test_company_dependent_reference_resolves_after_merge(self):
        Company = self.env["res.company"]
        company_a, company_b = Company.create(
            [{"name": "BPM-P1 A"}, {"name": "BPM-P1 B"}]
        )
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "cd src", "email": "cd@example.com"})
        dst = Partner.create({"name": "cd dst", "email": "cd@example.com"})
        bystander = Partner.create({"name": "cd bystander"})
        bystander.with_company(company_a).barcode = "BYSTANDER-A"

        src.with_company(company_a).barcode = "SRC-A"
        src.with_company(company_b).barcode = "SRC-B"

        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.env.invalidate_all()

        self.assertFalse(src.exists(), "source partner must be deleted after merge")
        self.assertEqual(
            dst.with_company(company_a).barcode,
            "SRC-A",
            "the source's per-company value must be carried onto the destination",
        )
        self.assertEqual(
            dst.with_company(company_b).barcode,
            "SRC-B",
            "each company slot must resolve independently after the merge",
        )
        self.assertEqual(
            bystander.with_company(company_a).barcode,
            "BYSTANDER-A",
            "an unrelated partner's per-company value must be left untouched",
        )


@tagged("post_install", "-at_install")
class TestMergePartnerAbsorbSourceValues(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["base.partner.merge.automatic.wizard"]
        cls.tag_dst = cls.env["res.partner.tag"].create({"name": "Kept"})
        cls.tag_src = cls.env["res.partner.tag"].create({"name": "Absorbed"})

    def _prepare_pair(self):
        dst = self.env["res.partner"].create(
            {"name": "Catch-All", "tag_ids": [Command.set(self.tag_dst.ids)]}
        )
        src = self.env["res.partner"].create(
            {
                "name": "Dormant",
                "vat": "BE0477472701",
                "street": "Rue Source 1",
                "tag_ids": [Command.set(self.tag_src.ids)],
            }
        )
        self.env["res.partner.bank"].create(
            {"acc_number": "BE55001234567890", "partner_id": src.id}
        )
        attachment = self.env["ir.attachment"].create(
            {"name": "Doc", "res_model": "res.partner", "res_id": src.id}
        )
        return dst, src, attachment

    def test_absorbing_is_the_default(self):
        dst, src, _attachment = self._prepare_pair()
        self.Wizard.create({})._merge([dst.id, src.id], dst, extra_checks=False)
        self.env.invalidate_all()

        self.assertEqual(dst.vat, "BE0477472701")
        self.assertEqual(dst.tag_ids, self.tag_dst | self.tag_src)
        self.assertTrue(dst.bank_ids)

    def test_not_absorbing_keeps_the_destination_identity(self):
        dst, src, attachment = self._prepare_pair()
        src.barcode = "SRC-BARCODE"
        wizard = self.Wizard.create({"absorb_source_values": False})
        wizard._merge([dst.id, src.id], dst, extra_checks=False)
        self.env.invalidate_all()

        self.assertFalse(src.exists(), "the source must still be merged away")
        self.assertEqual(
            attachment.res_id, dst.id, "references must be re-pointed either way"
        )
        self.assertFalse(dst.vat, "a plain field must not be absorbed")
        self.assertFalse(dst.street, "a plain field must not be absorbed")
        self.assertFalse(dst.barcode, "a company-dependent field must not be absorbed")
        self.assertEqual(dst.tag_ids, self.tag_dst, "a many2many must not be absorbed")
        self.assertFalse(dst.bank_ids, "a bank account must not be absorbed")

    def test_absorbing_a_uniqueness_constrained_value(self):
        dst, src, _attachment = self._prepare_pair()
        src.barcode = "SRC-BARCODE"

        self.Wizard.create({})._merge([dst.id, src.id], dst, extra_checks=False)
        self.env.invalidate_all()

        self.assertEqual(
            dst.barcode,
            "SRC-BARCODE",
            "the destination adopts the barcode once the source no longer holds it",
        )

    def test_not_absorbing_leaves_the_source_bank_account_behind(self):
        dst, src, _attachment = self._prepare_pair()
        bank = src.bank_ids
        wizard = self.Wizard.create({"absorb_source_values": False})
        wizard._merge([dst.id, src.id], dst, extra_checks=False)
        self.env.invalidate_all()

        self.assertFalse(
            bank.exists(),
            "an excluded bank account dies with its partner rather than moving",
        )


@tagged("post_install", "-at_install")
class TestMergePartnerGroupSize(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["base.partner.merge.automatic.wizard"]

    def test_a_group_larger_than_the_limit_is_merged_in_chunks(self):
        partners = self.env["res.partner"].create(
            [{"name": f"Dup {i}", "email": "dup@example.com"} for i in range(5)]
        )
        self.Wizard.create({})._merge_duplicate_group(partners.ids)
        self.env.invalidate_all()

        survivors = partners.exists()
        self.assertEqual(
            len(survivors), 1, "an automatic group must merge whatever its size"
        )

    def test_the_hand_picked_path_keeps_the_size_guardrail(self):
        partners = self.env["res.partner"].create(
            [{"name": f"Picked {i}", "email": "picked@example.com"} for i in range(4)]
        )
        wizard = self.Wizard.create(
            {"partner_ids": [Command.set(partners.ids)], "state": "selection"}
        )
        with self.assertRaises(UserError):
            wizard.action_merge()

    def test_grouping_on_no_identifying_field_is_refused(self):
        wizard = self.Wizard.create({"group_by_parent_id": True})
        with self.assertRaises(UserError):
            wizard.action_start_manual_process()


class TestMergePartnerDefaultsCache(TransactionCase):
    def _company_dependent_m2o(self):
        model = self.env["ir.model"].sudo().search([("model", "=", "res.partner")])
        self.env["ir.model.fields"].sudo().create(
            {
                "name": "x_merge_default_probe",
                "field_description": "Merge Default Probe",
                "model_id": model.id,
                "ttype": "many2one",
                "relation": "res.partner",
                "company_dependent": True,
                "state": "manual",
            }
        )
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr, [])
        return "x_merge_default_probe"

    def test_a_repointed_default_is_not_served_from_cache(self):
        fname = self._company_dependent_m2o()
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "dflt src", "email": "dflt@example.com"})
        dst = Partner.create({"name": "dflt dst", "email": "dflt@example.com"})

        self.env["ir.default"].set(
            "res.partner", fname, src.id, company_id=self.env.company.id
        )
        self.env.flush_all()
        self.assertEqual(
            self.env["ir.default"]._get_model_defaults("res.partner").get(fname),
            src.id,
            "the default must start out pointing at the source",
        )

        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.env.flush_all()

        self.assertFalse(src.exists(), "the wizard deletes the source")
        self.assertEqual(
            self.env["ir.default"]._get_model_defaults("res.partner").get(fname),
            dst.id,
            "the cached default must follow the merge, not keep the dead id",
        )

    def test_a_record_created_after_the_merge_gets_a_live_default(self):
        fname = self._company_dependent_m2o()
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "live src", "email": "live@example.com"})
        dst = Partner.create({"name": "live dst", "email": "live@example.com"})
        self.env["ir.default"].set(
            "res.partner", fname, src.id, company_id=self.env.company.id
        )
        self.env.flush_all()
        self.env["ir.default"]._get_model_defaults("res.partner")

        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.env.flush_all()

        fresh = Partner.create({"name": "created after the merge"})
        default = fresh[fname]
        self.assertTrue(
            default.exists(),
            "a record created after the merge must not default to a deleted partner",
        )
        self.assertEqual(default, dst)


@tagged("res_partner_merge")
class TestMergePartnerSimilarNames(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Wizard = cls.env["base.partner.merge.automatic.wizard"]
        if not cls.env.registry.has_trigram:
            raise unittest.SkipTest("pg_trgm is required for similar-name grouping")

    def _wizard(self, **values):
        return self.Wizard.create({"match_similar_names": True, **values})

    def test_a_near_miss_the_exact_criteria_cannot_see_is_grouped(self):
        keep = self.Partner.create({"name": "Acme Corporation"})
        dupe = self.Partner.create({"name": "Acme Corporatlon"})
        groups = self._wizard()._get_similar_name_groups(maximum_group=0)
        grouped = {pid for _min_id, ids in groups for pid in ids}
        self.assertLessEqual({keep.id, dupe.id}, grouped)

        exact = self.Wizard.create({"group_by_name": True})
        self.env.cr.execute(exact._generate_query(["name"]))
        exact_ids = {pid for _min_id, ids in self.env.cr.fetchall() for pid in ids}
        self.assertNotIn(
            dupe.id, exact_ids, "grouping on equal names cannot see a near miss"
        )

    def test_unrelated_names_are_not_grouped(self):
        left = self.Partner.create({"name": "Zenith Manufacturing"})
        right = self.Partner.create({"name": "Bakery Delights"})
        groups = self._wizard()._get_similar_name_groups(maximum_group=0)
        for _min_id, ids in groups:
            self.assertFalse(
                {left.id, right.id} <= set(ids), "unrelated names were merged"
            )

    def test_a_higher_threshold_rejects_what_a_lower_one_accepts(self):
        pair = {
            self.Partner.create({"name": "Northwind Traders"}).id,
            self.Partner.create({"name": "Northwind Trading"}).id,
        }
        wizard = self._wizard()
        param = self.env["ir.config_parameter"].sudo()

        def grouped_together():
            groups = wizard._get_similar_name_groups(maximum_group=0)
            return any(pair <= set(ids) for _min_id, ids in groups)

        param.set_param("base.partner_name_similarity_threshold", "0.7")
        self.assertTrue(grouped_together())

        param.set_param("base.partner_name_similarity_threshold", "0.999")
        self.assertFalse(grouped_together())

    def test_an_unusable_threshold_falls_back_to_the_default(self):
        wizard = self._wizard()
        param = self.env["ir.config_parameter"].sudo()
        for raw in ("", "not a number", "0", "1.5", "-0.3"):
            param.set_param("base.partner_name_similarity_threshold", raw)
            self.assertEqual(wizard._get_similar_name_threshold(), 0.75, f"raw={raw!r}")

    def test_three_mutually_similar_names_form_one_group_not_three(self):
        names = ["Globex Industries", "Globex Industrles", "Globex Industriez"]
        created = {self.Partner.create({"name": n}).id for n in names}
        groups = self._wizard()._get_similar_name_groups(maximum_group=0)
        holding = [ids for _min_id, ids in groups if created & set(ids)]
        self.assertEqual(len(holding), 1, "a cluster must not be split into pairs")
        self.assertLessEqual(created, set(holding[0]))

    def test_similar_names_alone_is_a_valid_selection(self):
        self.Partner.create({"name": "Umbrella Holdings"})
        self.Partner.create({"name": "Umbrella Holdlngs"})
        wizard = self._wizard()
        wizard.action_start_manual_process()
        self.assertEqual(wizard.state, "selection")
        self.assertGreaterEqual(wizard.number_group, 1)

    def test_paging_the_pairs_neither_loses_nor_splits_a_group(self):
        partners = self.Partner
        for stem in ("Initech Systems", "Hooli Networks", "Vandelay Imports"):
            partners |= self.Partner.create(
                [{"name": stem}, {"name": stem + "s"}, {"name": stem + " SA"}]
            )
        ids = partners.ids
        pairs = sorted(
            (left, right)
            for left in ids
            for right in ids
            if right > left
            and partners.browse(left).name[:6] == partners.browse(right).name[:6]
        )
        wizard = self._wizard()

        def page(self, limit, after=(0, 0)):
            return [pair for pair in pairs if pair > tuple(after)][:limit]

        with patch.object(type(wizard), "_get_similar_name_pairs", page):
            whole = wizard._get_similar_name_groups(maximum_group=0)
            with patch(
                "odoo.addons.base.wizards.base_partner_merge.SIMILAR_NAME_PAIR_BATCH", 2
            ):
                paged = wizard._get_similar_name_groups(maximum_group=0)
                first = wizard._get_similar_name_groups(maximum_group=1)
        self.assertEqual(len(whole), 3)
        self.assertEqual(paged, whole)
        self.assertEqual(first, whole[:1])

    def test_neither_exact_nor_similar_is_still_refused(self):
        with self.assertRaises(UserError):
            self.Wizard.create({}).action_start_manual_process()


@tagged("post_install", "-at_install")
class TestMergePartnerAbsorbsEditableComputes(TransactionCase):
    def test_stored_editable_computes_are_absorbed_from_the_source(self):
        Partner = self.env["res.partner"]
        salesperson = self.env["res.users"].search([("share", "=", False)], limit=1)
        src = Partner.create(
            {
                "name": "Absorb Src",
                "is_company": True,
                "email": "absorb@example.com",
                "company_registry": "REG-ABSORB",
                "user_id": salesperson.id,
            }
        )
        dst = Partner.create(
            {"name": "Absorb Dst", "is_company": True, "email": "absorb@example.com"}
        )
        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.assertEqual(
            dst.company_registry,
            "REG-ABSORB",
            "a stored editable compute must fill an empty destination",
        )
        self.assertEqual(dst.user_id, salesperson)


@tagged("post_install", "-at_install")
class TestMergePartnerIdentifiers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Type = cls.env["res.partner.identifier.type"]
        cls.single = Type.create(
            {
                "name": "Merge Single",
                "code": "MERGE_SINGLE",
                "pattern": r"[A-Z]{3,4}[0-9]{6}[A-Z0-9]{3}",
            }
        )
        cls.multi = Type.create(
            {
                "name": "Merge Multi",
                "code": "MERGE_MULTI",
                "multiple_per_contact": True,
                "unique_across_contacts": False,
            }
        )

    def _merge(self, src, dst):
        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )

    def test_a_single_per_contact_type_is_not_duplicated_on_the_destination(self):
        Partner = self.env["res.partner"]
        Identifier = self.env["res.partner.identifier"]
        src = Partner.create({"name": "Id Src", "is_company": True})
        dst = Partner.create({"name": "Id Dst", "is_company": True})
        Identifier.create(
            {"partner_id": src.id, "type_id": self.single.id, "value": "SRC010101AB1"}
        )
        Identifier.create(
            {"partner_id": dst.id, "type_id": self.single.id, "value": "DST010101AB1"}
        )
        self._merge(src, dst)
        rows = dst.identifier_ids.filtered(lambda i: i.type_id == self.single)
        self.assertEqual(
            len(rows),
            1,
            "the destination must not end with two values of a single-per-contact type",
        )
        self.assertEqual(rows.value, "DST010101AB1")

    def test_a_multiple_per_contact_type_keeps_distinct_values_and_drops_duplicates(
        self,
    ):
        Partner = self.env["res.partner"]
        Identifier = self.env["res.partner.identifier"]
        src = Partner.create({"name": "Id Src M", "is_company": True})
        dst = Partner.create({"name": "Id Dst M", "is_company": True})
        Identifier.create(
            {"partner_id": src.id, "type_id": self.multi.id, "value": "only-on-src"}
        )
        Identifier.create(
            {"partner_id": src.id, "type_id": self.multi.id, "value": "shared"}
        )
        Identifier.create(
            {"partner_id": dst.id, "type_id": self.multi.id, "value": "shared"}
        )
        self._merge(src, dst)
        values = sorted(
            dst.identifier_ids.filtered(lambda i: i.type_id == self.multi).mapped(
                "normalized_value"
            )
        )
        self.assertEqual(
            values,
            ["ONLYONSRC", "SHARED"],
            "a distinct source value moves; a duplicate of a value the "
            "destination already holds is dropped",
        )

    def test_phone_numbers_are_not_absorbed_when_values_are_not(self):
        Partner = self.env["res.partner"]
        src = Partner.create(
            {
                "name": "Phone Src NA",
                "phone_ids": [Command.create({"number": "555-9001", "type": "mobile"})],
            }
        )
        dst = Partner.create({"name": "Phone Dst NA"})

        wizard = self.env["base.partner.merge.automatic.wizard"].create(
            {"absorb_source_values": False}
        )
        wizard._merge([src.id, dst.id], dst)
        self.env.invalidate_all()

        self.assertFalse(src.exists())
        self.assertFalse(
            dst.phone_ids,
            "a catch-all destination must not accumulate the numbers of every "
            "contact merged into it -- `_merge_phone_numbers` ran unconditionally "
            "while the bank-account merge beside it was gated",
        )

    def test_a_reference_pair_with_an_unstored_model_field_is_skipped(self):
        # `automation.rule.trg_field_ref` is stored while the model_field it
        # names, `trg_field_ref_model_name`, is computed and unstored. Since
        # the pair is found with a domain over that model_field, including it
        # raised "Cannot convert ... to SQL because it is not stored" and took
        # every partner merge on a database carrying `automation` with it.
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        for (
            model_name,
            model_field,
            _field_name,
        ) in wizard._get_sidecar_reference_fields():
            model = self.env[model_name]
            self.assertTrue(
                model._fields[model_field].store,
                f"{model_name}.{model_field} names the model of a reference "
                "pair and must be stored, or the pair cannot be searched",
            )

    def test_identifier_survives_a_merge_that_does_not_absorb_source_values(self):
        Partner = self.env["res.partner"]
        Identifier = self.env["res.partner.identifier"]
        src = Partner.create({"name": "Id Src NA", "is_company": True})
        dst = Partner.create({"name": "Id Dst NA", "is_company": True})
        Identifier.create(
            {"partner_id": src.id, "type_id": self.single.id, "value": "SRC010101AB1"}
        )

        wizard = self.env["base.partner.merge.automatic.wizard"].create(
            {"absorb_source_values": False}
        )
        wizard._merge([src.id, dst.id], dst)
        self.env.invalidate_all()

        self.assertFalse(src.exists())
        rows = dst.identifier_ids.filtered(lambda i: i.type_id == self.single)
        self.assertEqual(
            rows.value,
            "SRC010101AB1",
            "MOD-1: the identifier must be repointed, not dropped, even when "
            "the merge does not absorb the source's other values",
        )


@tagged("post_install", "-at_install")
class TestMergePartnerSingleSourceClash(TransactionCase):
    def test_one_repeated_account_does_not_take_the_sources_others_with_it(self):
        Partner = self.env["res.partner"]
        Bank = self.env["res.partner.bank"]
        dst = Partner.create({"name": "clash dst", "email": "sc@example.com"})
        src = Partner.create({"name": "clash src", "email": "sc@example.com"})

        Bank.create({"acc_number": "SHARED-ACC", "partner_id": dst.id})
        bank_clash = Bank.create({"acc_number": "SHARED-ACC", "partner_id": src.id})
        bank_keep = Bank.create({"acc_number": "SRC-ONLY-ACC", "partner_id": src.id})

        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            (dst + src).ids, dst
        )
        self.env.invalidate_all()

        self.assertFalse(
            bank_clash.exists(),
            "the account the destination already holds is dropped",
        )
        self.assertTrue(
            bank_keep.exists(),
            "the source's other account must not be dropped with it",
        )
        self.assertEqual(bank_keep.partner_id, dst)
