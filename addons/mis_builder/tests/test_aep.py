# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime
import time

import odoo.tests.common as common
from odoo import fields
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from ..models.accounting_none import AccountingNone
from ..models.aep import AccountingExpressionProcessor as AEP
from ..models.aep import _is_domain


class TestAEP(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.res_company = self.env["res.company"]
        self.account_model = self.env["account.account"]
        self.move_model = self.env["account.move"]
        self.journal_model = self.env["account.journal"]
        self.curr_year = datetime.date.today().year
        self.prev_year = self.curr_year - 1
        # create company
        self.company = self.res_company.create({"name": "AEP Company"})
        # create receivable bs account
        self.account_ar = self.account_model.create(
            {
                "company_id": self.company.id,
                "code": "400AR",
                "name": "Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        # create income pl account
        self.account_in = self.account_model.create(
            {
                "company_id": self.company.id,
                "code": "700IN",
                "name": "Income",
                "account_type": "income",
            }
        )
        # create journal
        self.journal = self.journal_model.create(
            {
                "company_id": self.company.id,
                "name": "Sale journal",
                "code": "VEN",
                "type": "sale",
            }
        )
        # create move in December last year
        self._create_move(
            date=datetime.date(self.prev_year, 12, 1),
            amount=100,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        # create move in January this year
        self._create_move(
            date=datetime.date(self.curr_year, 1, 1),
            amount=300,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        # create move in March this year
        self._create_move(
            date=datetime.date(self.curr_year, 3, 1),
            amount=500,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        # create the AEP, and prepare the expressions we'll need
        self.aep = AEP(self.company)
        self.aep.parse_expr("bali[]")
        self.aep.parse_expr("bale[]")
        self.aep.parse_expr("balp[]")
        self.aep.parse_expr("balu[]")
        self.aep.parse_expr("bali[700IN]")
        self.aep.parse_expr("bale[700IN]")
        self.aep.parse_expr("balp[700IN]")
        self.aep.parse_expr("balp[700NA]")  # account that does not exist
        self.aep.parse_expr("bali[400AR]")
        self.aep.parse_expr("bale[400AR]")
        self.aep.parse_expr("balp[400AR]")
        self.aep.parse_expr("debp[400A%]")
        self.aep.parse_expr("crdp[700I%]")
        self.aep.parse_expr("bali[400%]")
        self.aep.parse_expr("bale[700%]")
        self.aep.parse_expr("balp[]" "[('account_id.code', '=', '400AR')]")
        self.aep.parse_expr(
            "balp[]" "[('account_id.account_type', '=', " " 'asset_receivable')]"
        )
        self.aep.parse_expr("balp[('account_type', '=', " "      'asset_receivable')]")
        self.aep.parse_expr(
            "balp['&', "
            "     ('account_type', '=', "
            "      'asset_receivable'), "
            "     ('code', '=', '400AR')]"
        )
        self.aep.parse_expr("bal_700IN")  # deprecated
        self.aep.parse_expr("bals[700IN]")  # deprecated

    def _create_move(self, date, amount, debit_acc, credit_acc, post=True):
        move = self.move_model.create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.to_string(date),
                "line_ids": [
                    (0, 0, {"name": "/", "debit": amount, "account_id": debit_acc.id}),
                    (
                        0,
                        0,
                        {"name": "/", "credit": amount, "account_id": credit_acc.id},
                    ),
                ],
            }
        )
        if post:
            move._post()
        return move

    def _do_queries(self, date_from, date_to):
        self.aep.do_queries(
            date_from=fields.Date.to_string(date_from),
            date_to=fields.Date.to_string(date_to),
        )

    def _eval(self, expr):
        eval_dict = {"AccountingNone": AccountingNone}
        return safe_eval(self.aep.replace_expr(expr), eval_dict)

    def _eval_by_account_id(self, expr):
        res = {}
        eval_dict = {"AccountingNone": AccountingNone}
        for account_id, replaced_exprs in self.aep.replace_exprs_by_account_id([expr]):
            res[account_id] = safe_eval(replaced_exprs[0], eval_dict)
        return res

    def test_sanity_check(self):
        self.assertEqual(self.company.fiscalyear_last_day, 31)
        self.assertEqual(self.company.fiscalyear_last_month, "12")

    def test_aep_basic(self):
        self.aep.done_parsing()
        # let's query for december
        self._do_queries(
            datetime.date(self.prev_year, 12, 1), datetime.date(self.prev_year, 12, 31)
        )
        # initial balance must be None
        self.assertIs(self._eval("bali[400AR]"), AccountingNone)
        self.assertIs(self._eval("bali[700IN]"), AccountingNone)
        # check variation
        self.assertEqual(self._eval("balp[400AR]"), 100)
        self.assertEqual(self._eval("balp[][('account_id.code', '=', '400AR')]"), 100)
        self.assertEqual(
            self._eval(
                "balp[]" "[('account_id.account_type', '=', " "  'asset_receivable')]"
            ),
            100,
        )
        self.assertEqual(
            self._eval("balp[('account_type', '=', " "      'asset_receivable')]"),
            100,
        )
        self.assertEqual(
            self._eval(
                "balp['&', "
                "     ('account_type', '=', "
                "      'asset_receivable'), "
                "     ('code', '=', '400AR')]"
            ),
            100,
        )
        self.assertEqual(self._eval("balp[700IN]"), -100)
        # check ending balance
        self.assertEqual(self._eval("bale[400AR]"), 100)
        self.assertEqual(self._eval("bale[700IN]"), -100)

        # let's query for January
        self._do_queries(
            datetime.date(self.curr_year, 1, 1), datetime.date(self.curr_year, 1, 31)
        )
        # initial balance is None for income account (it's not carried over)
        self.assertEqual(self._eval("bali[400AR]"), 100)
        self.assertIs(self._eval("bali[700IN]"), AccountingNone)
        # check variation
        self.assertEqual(self._eval("balp[400AR]"), 300)
        self.assertEqual(self._eval("balp[700IN]"), -300)
        # check ending balance
        self.assertEqual(self._eval("bale[400AR]"), 400)
        self.assertEqual(self._eval("bale[700IN]"), -300)
        # check result for non existing account
        self.assertIs(self._eval("bale[700NA]"), AccountingNone)

        # let's query for March
        self._do_queries(
            datetime.date(self.curr_year, 3, 1), datetime.date(self.curr_year, 3, 31)
        )
        # initial balance is the ending balance fo January
        self.assertEqual(self._eval("bali[400AR]"), 400)
        self.assertEqual(self._eval("bali[700IN]"), -300)
        self.assertEqual(self._eval("pbali[400AR]"), 400)
        self.assertEqual(self._eval("nbali[400AR]"), 0)
        self.assertEqual(self._eval("nbali[700IN]"), -300)
        self.assertEqual(self._eval("pbali[700IN]"), 0)
        # check variation
        self.assertEqual(self._eval("balp[400AR]"), 500)
        self.assertEqual(self._eval("balp[700IN]"), -500)
        self.assertEqual(self._eval("nbalp[400AR]"), 0)
        self.assertEqual(self._eval("pbalp[400AR]"), 500)
        self.assertEqual(self._eval("nbalp[700IN]"), -500)
        self.assertEqual(self._eval("pbalp[700IN]"), 0)
        # check ending balance
        self.assertEqual(self._eval("bale[400AR]"), 900)
        self.assertEqual(self._eval("nbale[400AR]"), 0)
        self.assertEqual(self._eval("pbale[400AR]"), 900)
        self.assertEqual(self._eval("bale[700IN]"), -800)
        self.assertEqual(self._eval("nbale[700IN]"), -800)
        self.assertEqual(self._eval("pbale[700IN]"), 0)
        # check some variant expressions, for coverage
        self.assertEqual(self._eval("crdp[700I%]"), 500)
        self.assertEqual(self._eval("debp[400A%]"), 500)
        self.assertEqual(self._eval("bal_700IN"), -500)
        self.assertEqual(self._eval("bals[700IN]"), -800)

        # unallocated p&l from previous year
        self.assertEqual(self._eval("balu[]"), -100)
        # TODO allocate profits, and then...

        # let's query for December where there is no data
        self._do_queries(
            datetime.date(self.curr_year, 12, 1), datetime.date(self.curr_year, 12, 31)
        )
        self.assertIs(self._eval("balp[700IN]"), AccountingNone)

    def test_aep_by_account(self):
        self.aep.done_parsing()
        self._do_queries(
            datetime.date(self.curr_year, 3, 1), datetime.date(self.curr_year, 3, 31)
        )
        variation = self._eval_by_account_id("balp[]")
        self.assertEqual(variation, {self.account_ar.id: 500, self.account_in.id: -500})
        variation = self._eval_by_account_id("pbalp[]")
        self.assertEqual(
            variation, {self.account_ar.id: 500, self.account_in.id: AccountingNone}
        )
        variation = self._eval_by_account_id("nbalp[]")
        self.assertEqual(
            variation, {self.account_ar.id: AccountingNone, self.account_in.id: -500}
        )
        variation = self._eval_by_account_id("balp[700IN]")
        self.assertEqual(variation, {self.account_in.id: -500})
        variation = self._eval_by_account_id("crdp[700IN] - debp[400AR]")
        self.assertEqual(variation, {self.account_ar.id: -500, self.account_in.id: 500})
        end = self._eval_by_account_id("bale[]")
        self.assertEqual(end, {self.account_ar.id: 900, self.account_in.id: -800})

    def test_aep_convenience_methods(self):
        initial = AEP.get_balances_initial(self.company, time.strftime("%Y") + "-03-01")
        self.assertEqual(
            initial, {self.account_ar.id: (400, 0), self.account_in.id: (0, 300)}
        )
        variation = AEP.get_balances_variation(
            self.company,
            time.strftime("%Y") + "-03-01",
            time.strftime("%Y") + "-03-31",
        )
        self.assertEqual(
            variation, {self.account_ar.id: (500, 0), self.account_in.id: (0, 500)}
        )
        end = AEP.get_balances_end(self.company, time.strftime("%Y") + "-03-31")
        self.assertEqual(
            end, {self.account_ar.id: (900, 0), self.account_in.id: (0, 800)}
        )
        unallocated = AEP.get_unallocated_pl(
            self.company, time.strftime("%Y") + "-03-15"
        )
        self.assertEqual(unallocated, (0, 100))

    def test_float_is_zero(self):
        dp = self.company.currency_id.decimal_places
        self.assertEqual(dp, 2)
        # make initial balance at Jan 1st equal to 0.01
        self._create_move(
            date=datetime.date(self.prev_year, 12, 1),
            amount=100.01,
            debit_acc=self.account_in,
            credit_acc=self.account_ar,
        )
        initial = AEP.get_balances_initial(self.company, time.strftime("%Y") + "-01-01")
        self.assertEqual(initial, {self.account_ar.id: (100.00, 100.01)})
        # make initial balance at Jan 1st equal to 0.001
        self._create_move(
            date=datetime.date(self.prev_year, 12, 1),
            amount=0.009,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        initial = AEP.get_balances_initial(self.company, time.strftime("%Y") + "-01-01")
        # epsilon initial balances is reported as empty
        self.assertEqual(initial, {})

    def test_get_account_ids_for_expr(self):
        self.aep.done_parsing()
        expr = "balp[700IN]"
        account_ids = self.aep.get_account_ids_for_expr(expr)
        self.assertEqual(account_ids, {self.account_in.id})
        expr = "balp[700%]"
        account_ids = self.aep.get_account_ids_for_expr(expr)
        self.assertEqual(account_ids, {self.account_in.id})
        expr = "bali[400%], bale[700%]"  # subkpis combined expression
        account_ids = self.aep.get_account_ids_for_expr(expr)
        self.assertEqual(account_ids, {self.account_in.id, self.account_ar.id})

    def test_get_aml_domain_for_expr(self):
        self.aep.done_parsing()
        expr = "balp[700IN]"
        domain = self.aep.get_aml_domain_for_expr(expr, "2017-01-01", "2017-03-31")
        self.assertEqual(
            domain,
            [
                ("account_id", "in", (self.account_in.id,)),
                "&",
                ("date", ">=", "2017-01-01"),
                ("date", "<=", "2017-03-31"),
            ],
        )
        expr = "debi[700IN] - crdi[400AR]"
        domain = self.aep.get_aml_domain_for_expr(expr, "2017-02-01", "2017-03-31")
        self.assertEqual(
            domain,
            [
                "|",
                # debi[700IN]
                "&",
                ("account_id", "in", (self.account_in.id,)),
                ("debit", "<>", 0.0),
                # crdi[400AR]
                "&",
                ("account_id", "in", (self.account_ar.id,)),
                ("credit", "<>", 0.0),
                "&",
                # for P&L accounts, only after fy start
                "|",
                ("date", ">=", "2017-01-01"),
                ("account_id.include_initial_balance", "=", True),
                # everything must be before from_date for initial balance
                ("date", "<", "2017-02-01"),
            ],
        )

    def test_is_domain(self):
        self.assertTrue(_is_domain("('a', '=' 1)"))
        self.assertTrue(_is_domain("'&', ('a', '=' 1), ('b', '=', 1)"))
        self.assertTrue(_is_domain("'|', ('a', '=' 1), ('b', '=', 1)"))
        self.assertTrue(_is_domain("'!', ('a', '=' 1), ('b', '=', 1)"))
        self.assertTrue(_is_domain("\"&\", ('a', '=' 1), ('b', '=', 1)"))
        self.assertTrue(_is_domain("\"|\", ('a', '=' 1), ('b', '=', 1)"))
        self.assertTrue(_is_domain("\"!\", ('a', '=' 1), ('b', '=', 1)"))
        self.assertFalse(_is_domain("123%"))
        self.assertFalse(_is_domain("123%,456"))
        self.assertFalse(_is_domain(""))

    def test_inactive_tax(self):
        expr = 'balp[][("tax_ids.name", "=", "test tax")]'
        self.aep.parse_expr(expr)
        self.aep.done_parsing()

        tax = self.env["account.tax"].create(
            dict(name="test tax", active=True, amount=0, company_id=self.company.id)
        )
        move = self._create_move(
            date=datetime.date(self.prev_year, 12, 1),
            amount=100,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
            post=False,
        )
        for ml in move.line_ids:
            if ml.credit:
                ml.write(dict(tax_ids=[(6, 0, [tax.id])]))
        tax.active = False
        move._post()
        # let's query for december 1st
        self._do_queries(
            datetime.date(self.prev_year, 12, 1), datetime.date(self.prev_year, 12, 1)
        )
        # let's see if there was a match
        self.assertEqual(self._eval(expr), -100)

    def test_invalid_field(self):
        expr = 'balp[][("invalid_field", "=", "...")]'
        self.aep.parse_expr(expr)
        self.aep.done_parsing()
        with self.assertRaises(UserError) as cm:
            self._do_queries(
                datetime.date(self.prev_year, 12, 1),
                datetime.date(self.prev_year, 12, 1),
            )
        assert "Error while querying move line source" in str(cm.exception)
