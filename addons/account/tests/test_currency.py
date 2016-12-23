from openerp.osv import orm
from openerp.tests.common import TransactionCase

class TestSearch(TransactionCase):
    """Tests for search on name_search (account.account)

    The name search on account.account is quite complexe, make sure
    we have all the correct results
    """

    def test_move_line_amount_in_currency_no_currency(self):
        account_move_obj = self.registry("account.move")
        defaults = account_move_obj.default_get(self.cr, self.uid,
                                                ["period_id", "date"])
        ref = self.ref

        with self.assertRaises(orm.except_orm):
            account_move_obj.create(
                self.cr, self.uid,
                {
                    "journal_id": ref("account.sales_journal"),
                    "period_id": defaults["period_id"],
                    "date": defaults["date"],
                    "line_id": [
                        (0, 0, {
                            "name": "Test Line",
                            "account_id": ref("account.cash"),
                            "debit": 5.00,
                            "amount_currency": 5.00,
                        }),
                    ],
                }
            )


    def test_move_line_no_amount_in_currency_with_currency(self):
        account_move_obj = self.registry("account.move")
        defaults = account_move_obj.default_get(self.cr, self.uid,
                                                ["period_id", "date"])
        ref = self.ref

        with self.assertRaises(orm.except_orm):
            account_move_obj.create(
                self.cr, self.uid,
                {
                    "journal_id": ref("account.sales_journal"),
                    "period_id": defaults["period_id"],
                    "date": defaults["date"],
                    "line_id": [
                        (0, 0, {
                            "name": "Test Line",
                            "account_id": ref("account.usd_bnk"),
                            "debit": 5.00,
                            "amount_currency": 0.00,
                            "currency_id": ref("base.USD"),
                        }),
                    ],
                }
            )


