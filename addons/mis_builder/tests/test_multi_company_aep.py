# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime

import odoo.tests.common as common
from odoo import fields
from odoo.tools.safe_eval import safe_eval

from ..models.accounting_none import AccountingNone
from ..models.aep import AccountingExpressionProcessor as AEP


class TestMultiCompanyAEP(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.res_company = self.env["res.company"]
        self.account_model = self.env["account.account"]
        self.move_model = self.env["account.move"]
        self.journal_model = self.env["account.journal"]
        self.currency_model = self.env["res.currency"]
        self.curr_year = datetime.date.today().year
        self.prev_year = self.curr_year - 1
        self.usd = self.currency_model.with_context(active_test=False).search(
            [("name", "=", "USD")]
        )
        self.eur = self.currency_model.with_context(active_test=False).search(
            [("name", "=", "EUR")]
        )
        # create company A and B
        self.company_eur = self.res_company.create(
            {"name": "CYEUR", "currency_id": self.eur.id}
        )
        self.company_usd = self.res_company.create(
            {"name": "CYUSD", "currency_id": self.usd.id}
        )
        self.env["res.currency.rate"].search([]).unlink()
        for company, divider in [(self.company_eur, 1.0), (self.company_usd, 2.0)]:
            # create receivable bs account
            company_key = company.name
            setattr(
                self,
                "account_ar_" + company_key,
                self.account_model.create(
                    {
                        "company_id": company.id,
                        "code": "400AR",
                        "name": "Receivable",
                        "account_type": "asset_receivable",
                        "reconcile": True,
                    }
                ),
            )
            # create income pl account
            setattr(
                self,
                "account_in_" + company_key,
                self.account_model.create(
                    {
                        "company_id": company.id,
                        "code": "700IN",
                        "name": "Income",
                        "account_type": "income",
                    }
                ),
            )
            # create journal
            setattr(
                self,
                "journal" + company_key,
                self.journal_model.create(
                    {
                        "company_id": company.id,
                        "name": "Sale journal",
                        "code": "VEN",
                        "type": "sale",
                    }
                ),
            )
            # create move in december last year
            self._create_move(
                journal=getattr(self, "journal" + company_key),
                date=datetime.date(self.prev_year, 12, 1),
                amount=100 / divider,
                debit_acc=getattr(self, "account_ar_" + company_key),
                credit_acc=getattr(self, "account_in_" + company_key),
            )
            # create move in january this year
            self._create_move(
                journal=getattr(self, "journal" + company_key),
                date=datetime.date(self.curr_year, 1, 1),
                amount=300 / divider,
                debit_acc=getattr(self, "account_ar_" + company_key),
                credit_acc=getattr(self, "account_in_" + company_key),
            )
            # create move in february this year
            self._create_move(
                journal=getattr(self, "journal" + company_key),
                date=datetime.date(self.curr_year, 3, 1),
                amount=500 / divider,
                debit_acc=getattr(self, "account_ar_" + company_key),
                credit_acc=getattr(self, "account_in_" + company_key),
            )

    def _create_move(self, journal, date, amount, debit_acc, credit_acc):
        move = self.move_model.create(
            {
                "journal_id": journal.id,
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
        move._post()
        return move

    def _do_queries(self, companies, currency, date_from, date_to):
        # create the AEP, and prepare the expressions we'll need
        aep = AEP(companies, currency)
        aep.parse_expr("bali[]")
        aep.parse_expr("bale[]")
        aep.parse_expr("balp[]")
        aep.parse_expr("balu[]")
        aep.parse_expr("bali[700IN]")
        aep.parse_expr("bale[700IN]")
        aep.parse_expr("balp[700IN]")
        aep.parse_expr("bali[400AR]")
        aep.parse_expr("bale[400AR]")
        aep.parse_expr("balp[400AR]")
        aep.parse_expr("debp[400A%]")
        aep.parse_expr("crdp[700I%]")
        aep.parse_expr("bali[400%]")
        aep.parse_expr("bale[700%]")
        aep.done_parsing()
        aep.do_queries(
            date_from=fields.Date.to_string(date_from),
            date_to=fields.Date.to_string(date_to),
        )
        return aep

    def _eval(self, aep, expr):
        eval_dict = {"AccountingNone": AccountingNone}
        return safe_eval(aep.replace_expr(expr), eval_dict)

    def _eval_by_account_id(self, aep, expr):
        res = {}
        eval_dict = {"AccountingNone": AccountingNone}
        for account_id, replaced_exprs in aep.replace_exprs_by_account_id([expr]):
            res[account_id] = safe_eval(replaced_exprs[0], eval_dict)
        return res

    def test_aep_basic(self):
        # let's query for december, one company
        aep = self._do_queries(
            self.company_eur,
            None,
            datetime.date(self.prev_year, 12, 1),
            datetime.date(self.prev_year, 12, 31),
        )
        self.assertEqual(self._eval(aep, "balp[700IN]"), -100)
        aep = self._do_queries(
            self.company_usd,
            None,
            datetime.date(self.prev_year, 12, 1),
            datetime.date(self.prev_year, 12, 31),
        )
        self.assertEqual(self._eval(aep, "balp[700IN]"), -50)
        # let's query for december, two companies
        aep = self._do_queries(
            self.company_eur | self.company_usd,
            self.eur,
            datetime.date(self.prev_year, 12, 1),
            datetime.date(self.prev_year, 12, 31),
        )
        self.assertEqual(self._eval(aep, "balp[700IN]"), -150)

    def test_aep_multi_currency(self):
        date_from = datetime.date(self.prev_year, 12, 1)
        date_to = datetime.date(self.prev_year, 12, 31)
        today = datetime.date.today()
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd.id, name=date_to, rate=1.1)
        )
        self.env["res.currency.rate"].create(
            dict(currency_id=self.usd.id, name=today, rate=1.2)
        )
        # let's query for december, one company, default currency = eur
        aep = self._do_queries(self.company_eur, None, date_from, date_to)
        self.assertEqual(self._eval(aep, "balp[700IN]"), -100)
        # let's query for december, two companies
        aep = self._do_queries(
            self.company_eur | self.company_usd, self.eur, date_from, date_to
        )
        self.assertAlmostEqual(self._eval(aep, "balp[700IN]"), -100 - 50 / 1.1)
        # let's query for december, one company, currency = usd
        aep = self._do_queries(self.company_eur, self.usd, date_from, date_to)
        self.assertAlmostEqual(self._eval(aep, "balp[700IN]"), -100 * 1.1)
        # let's query for december, two companies, currency = usd
        aep = self._do_queries(
            self.company_eur | self.company_usd, self.usd, date_from, date_to
        )
        self.assertAlmostEqual(self._eval(aep, "balp[700IN]"), -100 * 1.1 - 50)
