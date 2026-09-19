from odoo.tests.common import TransactionCase, tagged


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
