from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestMixinMergeSidecars(TransactionCase):
    def setUp(self):
        super().setUp()
        self.wizard = self.env["base.partner.merge.automatic.wizard"].create({})

    def test_the_sidecar_list_comes_from_the_registry(self):
        sidecars = self.wizard._get_sidecar_reference_fields()
        self.assertIn(("ir.attachment", "res_model", "res_id"), sidecars)
        self.assertIn(("ir.model.data", "model", "res_id"), sidecars)
        for model, field_model, field_id in sidecars:
            field = self.env[model]._fields[field_id]
            self.assertTrue(field.store and field.is_many2one_reference)
            self.assertEqual(field.model_field, field_model)

    def test_a_unique_index_counts_as_a_clash_guard(self):
        self.env.cr.execute(
            "CREATE TABLE test_merge_uix (id serial PRIMARY KEY, partner_id int)"
        )
        self.assertFalse(
            self.wizard._has_check_or_unique_constraint("test_merge_uix", "partner_id")
        )
        self.env.cr.execute(
            "CREATE UNIQUE INDEX test_merge_uix_partner ON test_merge_uix (partner_id)"
        )
        self.assertTrue(
            self.wizard._has_check_or_unique_constraint("test_merge_uix", "partner_id")
        )

    @mute_logger("odoo.addons.base.merge")
    def test_a_clashing_follower_drops_only_itself(self):
        if "mail.followers" not in self.env.registry:
            self.skipTest("mail is not installed")
        Partner = self.env["res.partner"]
        dst, src, shared, only_src = (
            Partner.create({"name": name})
            for name in ("merge dst", "merge src", "follower shared", "follower src")
        )
        dst.message_subscribe(partner_ids=shared.ids)
        src.message_subscribe(partner_ids=(shared + only_src).ids)
        self.env.flush_all()

        self.wizard._update_reference_fields_generic("res.partner", src, dst)

        self.assertEqual(
            dst.message_partner_ids,
            shared + only_src,
            "the follower src alone had must move; only the duplicate is dropped",
        )
        self.assertFalse(src.message_partner_ids)

    def test_a_reference_on_an_archived_record_is_repointed(self):
        Action = self.env["ir.actions.act_window"]
        src, dst = (
            Action.create({"name": name, "res_model": "res.partner"})
            for name in ("merge src action", "merge dst action")
        )
        Menu = self.env["ir.ui.menu"]
        live, archived = (
            Menu.create(
                {
                    "name": name,
                    "action": f"ir.actions.act_window,{src.id}",
                    "active": active,
                }
            )
            for name, active in (
                ("merge live menu", True),
                ("merge archived menu", False),
            )
        )
        self.env.flush_all()

        self.wizard._update_reference_fields_generic("ir.actions.act_window", src, dst)
        self.env.invalidate_all()

        self.assertEqual(live.action, dst)
        self.assertEqual(
            archived.action,
            dst,
            "an archived record kept pointing at the source, which the merge deletes",
        )

    def test_foreign_keys_repoint_on_a_model_other_than_partner(self):
        Tag = self.env["res.partner.tag"]
        src, dst = (
            Tag.create({"name": name}) for name in ("merge src tag", "merge dst tag")
        )
        child = Tag.create({"name": "merge child tag", "parent_id": src.id})
        Partner = self.env["res.partner"]
        only_src = Partner.create(
            {"name": "tagged src", "tag_ids": [Command.set(src.ids)]}
        )
        both = Partner.create(
            {"name": "tagged both", "tag_ids": [Command.set((src + dst).ids)]}
        )
        self.env.flush_all()

        self.wizard._update_foreign_keys_generic("res.partner.tag", src, dst)
        self.env.invalidate_all()

        self.assertEqual(child.parent_id, dst, "a plain foreign key is repointed")
        self.assertEqual(
            only_src.tag_ids, dst, "a join row without a clash is repointed"
        )
        self.assertEqual(
            both.tag_ids,
            src + dst,
            "a join row that would duplicate the destination is left for the "
            "source's deletion to cascade",
        )
        src.unlink()
        self.env.invalidate_all()
        self.assertEqual(both.tag_ids, dst)


@tagged("post_install", "-at_install")
class TestMixinMergeSummableCompanyDependent(TransactionCase):
    def _company_dependent_integer(self):
        model = self.env["ir.model"].sudo().search([("model", "=", "res.partner")])
        self.env["ir.model.fields"].sudo().create(
            {
                "name": "x_merge_sum_probe",
                "field_description": "Merge Sum Probe",
                "model_id": model.id,
                "ttype": "integer",
                "company_dependent": True,
                "state": "manual",
            }
        )
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr, [])
        return "x_merge_sum_probe"

    def test_a_summable_company_dependent_field_is_summed_per_company(self):
        fname = self._company_dependent_integer()
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "merge sum company b"})
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "sum src"})
        dst = Partner.create({"name": "sum dst"})
        src.with_company(company_a)[fname] = 5
        src.with_company(company_b)[fname] = 7
        dst.with_company(company_a)[fname] = 10
        dst.with_company(company_b)[fname] = 3
        self.env.flush_all()

        self.env["base.partner.merge.automatic.wizard"].create(
            {}
        )._update_values_generic(src, dst, summable_fields=[fname])
        self.env.invalidate_all()

        self.assertEqual(dst.with_company(company_a)[fname], 15)
        self.assertEqual(
            dst.with_company(company_b)[fname],
            10,
            "a summable company-dependent field is summed in every company, "
            "not only the current one",
        )

    def test_a_company_dependent_field_that_is_not_summable_takes_the_destination(
        self,
    ):
        fname = self._company_dependent_integer()
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "merge keep company b"})
        company_c = self.env["res.company"].create({"name": "merge keep company c"})
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "keep src"})
        dst = Partner.create({"name": "keep dst"})
        src.with_company(company_a)[fname] = 5
        src.with_company(company_b)[fname] = 7
        src.with_company(company_c)[fname] = 9
        dst.with_company(company_a)[fname] = 10
        dst.with_company(company_b)[fname] = 3
        self.env.flush_all()

        self.env["base.partner.merge.automatic.wizard"].create(
            {}
        )._update_values_generic(src, dst)
        self.env.invalidate_all()

        self.assertEqual(dst.with_company(company_a)[fname], 10)
        self.assertEqual(dst.with_company(company_b)[fname], 3)
        self.assertEqual(
            dst.with_company(company_c)[fname],
            9,
            "a company where only the source held a value takes the source's",
        )
