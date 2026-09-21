from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCompanyConfig(TransactionCase):
    def test_one_record_per_company_created_on_first_read(self):
        Config = self.env["test_orm.company_config"]
        company = self.env["res.company"].create({"name": "config co"})
        self.assertFalse(Config.search([("company_id", "=", company.id)]))
        config = Config._for(company)
        self.assertEqual(config.company_id, company)
        self.assertEqual(config.limit, 3)
        self.assertEqual(Config._for(company), config)
        again = Config.create({"company_id": company.id, "limit": 7})
        self.assertEqual(again, config)
        self.assertEqual(config.limit, 7)
        self.assertEqual(Config.search_count([("company_id", "=", company.id)]), 1)

    def test_for_each_fills_the_missing_companies_only(self):
        Config = self.env["test_orm.company_config"]
        first = self.env["res.company"].create({"name": "first co"})
        second = self.env["res.company"].create({"name": "second co"})
        one = Config._for(first)
        both = Config._for_each(first | second)
        self.assertEqual(len(both), 2)
        self.assertIn(one, both)
        self.assertEqual(both.company_id, first | second)

    def test_deleting_the_company_deletes_its_configuration(self):
        Config = self.env["test_orm.company_config"]
        self.assertEqual(Config._fields["company_id"].ondelete, "cascade")
        self.env.cr.execute(
            """
            SELECT confdeltype
              FROM pg_constraint
             WHERE conrelid = %s::regclass
               AND contype = 'f'
               AND confrelid = 'res_company'::regclass
            """,
            [Config._table],
        )
        self.assertEqual(self.env.cr.fetchall(), [("c",)])

    def _config_models(self):
        return [
            self.env[name]
            for name, model in self.env.registry.items()
            if getattr(model, "_company_config", False) and not model._abstract
        ]

    def test_every_configuration_model_is_scoped_by_a_company_rule(self):
        Rule = self.env["ir.rule"].sudo()
        for Config in self._config_models():
            with self.subTest(model=Config._name):
                rules = Rule.search([("model_id.model", "=", Config._name)])
                self.assertTrue(
                    any("company_id" in rule.domain_force for rule in rules),
                    f"{Config._name} ships no record rule on company_id",
                )

    def test_a_configuration_is_read_in_the_callers_scope(self):
        Config = self.env["test_orm.company_config"]
        mine = self.env["res.company"].create({"name": "scope mine co"})
        theirs = self.env["res.company"].create({"name": "scope theirs co"})
        Config._for(theirs).sudo().write({"limit": 42})
        user = new_test_user(
            self.env,
            login="cc_scope_user",
            groups="base.group_user",
            company_id=mine.id,
            company_ids=[Command.set([mine.id])],
        )
        as_user = Config.with_user(user).with_context(allowed_company_ids=mine.ids)
        self.assertEqual(as_user._for(mine).company_id, mine)
        self.assertFalse(as_user._for(mine).sudo(False).env.su)
        with self.assertRaises(AccessError):
            as_user._for(theirs).limit
        self.assertEqual(as_user.search([]).company_id, mine)
        self.assertFalse(
            as_user.search([("limit", "=", 42)]),
            "a search is bounded by the reader's rules",
        )

    def test_a_reader_without_access_finds_nothing_through_the_link(self):
        company = self.env["res.company"].create({"name": "no access co"})
        self.env["test_orm.company_config"]._for(company).sudo().write({"limit": 7})
        portal = new_test_user(
            self.env,
            login="cc_portal",
            groups="base.group_portal",
            company_id=company.id,
            company_ids=[Command.set([company.id])],
        )
        Company = self.env["res.company"].with_user(portal)
        Company = Company.with_context(allowed_company_ids=company.ids)
        self.assertEqual(Company.browse(company.id).name, "no access co")
        as_portal = self.env["test_orm.company_config"].with_user(portal)
        as_portal = as_portal.with_context(allowed_company_ids=company.ids)
        with self.assertRaises(AccessError):
            as_portal.search([("limit", "=", 7)])
        with self.assertRaises(AccessError):
            as_portal._for(company).limit
