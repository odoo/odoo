from odoo.tests.common import TransactionCase


class TestAccountFiscalYearGovClosure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        if "gov_public_accounting_enabled" in cls.company._fields:
            cls.company.write({"gov_public_accounting_enabled": True})

        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY 2025",
                "company_id": cls.company.id,
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Diario GOV Fechamento",
                "code": "GV25",
                "type": "general",
                "company_id": cls.company.id,
            }
        )

    def test_reporting_ready_when_fiscal_and_journal_locks_cover_year_end(self):
        self.company.write({"fiscalyear_lock_date": self.fiscal_year.date_to})
        if "journal_lock_date" in self.journal._fields:
            self.journal.write({"journal_lock_date": self.fiscal_year.date_to})

        status = self.fiscal_year.get_gov_closure_status()

        self.assertTrue(status["fiscal_lock_satisfied"])
        self.assertTrue(status["journal_lock_complete"])
        self.assertTrue(self.fiscal_year.is_gov_reporting_ready())

    def test_reporting_not_ready_when_fiscal_lock_is_before_year_end(self):
        self.company.write({"fiscalyear_lock_date": "2025-12-01"})
        if "journal_lock_date" in self.journal._fields:
            self.journal.write({"journal_lock_date": self.fiscal_year.date_to})

        status = self.fiscal_year.get_gov_closure_status()

        self.assertFalse(status["fiscal_lock_satisfied"])
        self.assertFalse(self.fiscal_year.is_gov_reporting_ready())
