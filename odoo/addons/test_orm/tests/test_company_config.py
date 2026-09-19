from psycopg import IntegrityError

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


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
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                Config.create({"company_id": company.id})

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
        company = self.env["res.company"].create({"name": "gone co"})
        config = Config._for(company)
        self.env.user.company_ids -= company
        company.unlink()
        self.assertFalse(config.exists())
