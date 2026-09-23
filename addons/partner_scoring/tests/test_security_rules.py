from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.query import Query


@tagged("post_install", "-at_install", "partner_scoring")
class TestSecurityRules(TransactionCase):
    """The scoring models must not disclose partners their reader cannot see."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "Rules Company B"})
        cls.outsider = cls.env["res.users"].create(
            {
                "name": "Rules Outsider",
                "login": "rules_outsider",
                "company_id": cls.company_b.id,
                "company_ids": [Command.set(cls.company_b.ids)],
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.attribute = cls.env["res.partner.attribute"].create(
            {"name": "Rules Attr", "value_type": "single"}
        )
        cls.value = cls.env["res.partner.attribute.value"].create(
            {
                "name": "Rules Value",
                "attribute_id": cls.attribute.id,
                "score_value": 10.0,
            }
        )
        cls.hidden = cls.env["res.partner"].create(
            {
                "name": "Rules Hidden Partner",
                "is_company": True,
                "company_id": cls.company_a.id,
            }
        )
        cls.line = cls.env["res.partner.attribute.line"].create(
            {
                "partner_id": cls.hidden.id,
                "attribute_id": cls.attribute.id,
                "value_ids": [Command.set(cls.value.ids)],
            }
        )
        cls.hidden._score_refresh()

    def test_the_partner_itself_is_hidden(self):
        """The premise: without this the rules below prove nothing."""
        as_outsider = self.env["res.partner"].with_user(self.outsider)
        self.assertFalse(as_outsider.search([("id", "=", self.hidden.id)]))

    def test_the_score_breakdown_follows_the_partner(self):
        score_model = self.env["partner.score.line"].with_user(self.outsider)
        self.assertTrue(self.hidden.score_line_ids)
        self.assertFalse(score_model.search([("subject_id", "=", self.hidden.id)]))
        with self.assertRaises(AccessError):
            self.hidden.score_line_ids.with_user(self.outsider).read(["source_ref"])

    def test_the_captured_attributes_follow_the_partner(self):
        line_model = self.env["res.partner.attribute.line"].with_user(self.outsider)
        self.assertFalse(line_model.search([("partner_id", "=", self.hidden.id)]))
        as_outsider = self.line.with_user(self.outsider)
        with self.assertRaises(AccessError):
            as_outsider.read(["value_ids"])
        with self.assertRaises(AccessError):
            as_outsider.write({"value_ids": [Command.clear()]})
        with self.assertRaises(AccessError):
            as_outsider.unlink()

    def test_the_rule_domain_outlives_the_request_that_built_it(self):
        """The domain is cached for the registry's life, so it must hold no Query."""
        for model in ("partner.score.line", "res.partner.attribute.line"):
            domain = self.env[model].with_user(self.outsider)._access_domain("read")
            self.assertFalse(
                [c for c in domain.iter_conditions() if isinstance(c.value, Query)],
                f"the {model} rule caches a Query, and its cursor is closed by the "
                "time the next request reads the cache",
            )

    def test_an_archived_partner_keeps_its_lines_readable(self):
        """Archiving is not a permission: whoever read the partner still reads it."""
        insider = self.env["res.users"].create(
            {
                "name": "Rules Insider",
                "login": "rules_insider",
                "company_id": self.company_a.id,
                "company_ids": [Command.set(self.company_a.ids)],
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        self.line.with_user(insider).read(["attribute_id"])
        self.hidden.action_archive()
        self.env.registry.clear_cache()
        self.line.with_user(insider).read(["attribute_id"])

    def test_a_foreign_company_scale_is_not_disclosed(self):
        profile_model = self.env["partner.tier"]
        mine = profile_model.create(
            {
                "name": "Rules Band B",
                "min_value": 0.0,
                "max_value": 0.0,
                "company_id": self.company_b.id,
            }
        )
        theirs = profile_model.create(
            {
                "name": "Rules Band A",
                "min_value": 0.0,
                "max_value": 0.0,
                "company_id": self.company_a.id,
            }
        )
        visible = profile_model.with_user(self.outsider).search(
            [("id", "in", (mine | theirs).ids)]
        )
        self.assertEqual(visible, mine)

    def test_the_overlap_check_still_sees_foreign_bands(self):
        """The company rule must not weaken the band constraint."""
        self.env["partner.tier"].create(
            {
                "name": "Rules Band A Wide",
                "min_value": 0.0,
                "max_value": 0.0,
                "company_id": self.company_a.id,
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Rules Manager B",
                "login": "rules_manager_b",
                "company_id": self.company_b.id,
                "company_ids": [Command.set(self.company_b.ids)],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "partner_scoring.group_partner_scoring_manager"
                            ).id,
                        ]
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            self.env["partner.tier"].with_user(manager).create(
                {
                    "name": "Rules Shared Overlap",
                    "min_value": 0.0,
                    "max_value": 0.0,
                    "company_id": False,
                }
            )
