# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common

from ..models.accounting_none import AccountingNone
from ..models.mis_report import CMP_DIFF
from ..models.mis_report_instance import (
    MODE_NONE,
    SRC_ACTUALS_ALT,
    SRC_CMPCOL,
    SRC_SUMCOL,
)
from .common import assert_matrix


class TestMisReportInstanceDataSources(common.TransactionCase):
    """Test sum and comparison data source."""

    def _create_move(self, date, amount, debit_acc, credit_acc):
        move = self.move_model.create(
            {
                "journal_id": self.journal.id,
                "date": date,
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

    def setUp(self):
        super().setUp()
        self.account_model = self.env["account.account"]
        self.move_model = self.env["account.move"]
        self.journal_model = self.env["account.journal"]
        # create receivable bs account
        self.account_ar = self.account_model.create(
            {
                "company_id": self.env.user.company_id.id,
                "code": "400AR",
                "name": "Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        # create income account
        self.account_in = self.account_model.create(
            {
                "company_id": self.env.user.company_id.id,
                "code": "700IN",
                "name": "Income",
                "account_type": "income",
            }
        )
        self.account_in2 = self.account_model.create(
            {
                "company_id": self.env.user.company_id.id,
                "code": "700IN2",
                "name": "Income",
                "account_type": "income",
            }
        )
        # create journal
        self.journal = self.journal_model.create(
            {
                "company_id": self.env.user.company_id.id,
                "name": "Sale journal",
                "code": "VEN",
                "type": "sale",
            }
        )
        # create move
        self._create_move(
            date="2017-01-01",
            amount=11,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        # create move
        self._create_move(
            date="2017-02-01",
            amount=13,
            debit_acc=self.account_ar,
            credit_acc=self.account_in,
        )
        self._create_move(
            date="2017-02-01",
            amount=17,
            debit_acc=self.account_ar,
            credit_acc=self.account_in2,
        )
        # create report
        self.report = self.env["mis.report"].create(dict(name="test report"))
        self.kpi1 = self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                name="k1",
                description="kpi 1",
                expression="-balp[700IN]",
                compare_method=CMP_DIFF,
            )
        )
        self.expr1 = self.kpi1.expression_ids[0]
        self.kpi2 = self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                name="k2",
                description="kpi 2",
                expression="-balp[700%]",
                compare_method=CMP_DIFF,
                auto_expand_accounts=True,
            )
        )
        self.instance = self.env["mis.report.instance"].create(
            dict(name="test instance", report_id=self.report.id, comparison_mode=True)
        )
        self.p1 = self.env["mis.report.instance.period"].create(
            dict(
                name="p1",
                report_instance_id=self.instance.id,
                manual_date_from="2017-01-01",
                manual_date_to="2017-01-31",
            )
        )
        self.p2 = self.env["mis.report.instance.period"].create(
            dict(
                name="p2",
                report_instance_id=self.instance.id,
                manual_date_from="2017-02-01",
                manual_date_to="2017-02-28",
            )
        )

    def test_sum(self):
        self.psum = self.env["mis.report.instance.period"].create(
            dict(
                name="psum",
                report_instance_id=self.instance.id,
                mode=MODE_NONE,
                source=SRC_SUMCOL,
                source_sumcol_ids=[
                    (0, 0, dict(period_to_sum_id=self.p1.id, sign="+")),
                    (0, 0, dict(period_to_sum_id=self.p2.id, sign="+")),
                ],
            )
        )
        matrix = self.instance._compute_matrix()
        # None in last col because account details are not summed by default
        assert_matrix(
            matrix,
            [
                [11, 13, 24],
                [11, 30, 41],
                [11, 13, AccountingNone],
                [AccountingNone, 17, AccountingNone],
            ],
        )

    def test_sum_diff(self):
        self.psum = self.env["mis.report.instance.period"].create(
            dict(
                name="psum",
                report_instance_id=self.instance.id,
                mode=MODE_NONE,
                source=SRC_SUMCOL,
                source_sumcol_ids=[
                    (0, 0, dict(period_to_sum_id=self.p1.id, sign="+")),
                    (0, 0, dict(period_to_sum_id=self.p2.id, sign="-")),
                ],
                source_sumcol_accdet=True,
            )
        )
        matrix = self.instance._compute_matrix()
        assert_matrix(
            matrix,
            [[11, 13, -2], [11, 30, -19], [11, 13, -2], [AccountingNone, 17, -17]],
        )

    def test_cmp(self):
        self.pcmp = self.env["mis.report.instance.period"].create(
            dict(
                name="pcmp",
                report_instance_id=self.instance.id,
                mode=MODE_NONE,
                source=SRC_CMPCOL,
                source_cmpcol_from_id=self.p1.id,
                source_cmpcol_to_id=self.p2.id,
            )
        )
        matrix = self.instance._compute_matrix()
        assert_matrix(
            matrix, [[11, 13, 2], [11, 30, 19], [11, 13, 2], [AccountingNone, 17, 17]]
        )

    def test_actuals(self):
        matrix = self.instance._compute_matrix()
        assert_matrix(matrix, [[11, 13], [11, 30], [11, 13], [AccountingNone, 17]])

    def test_actuals_disable_auto_expand_accounts(self):
        self.instance.no_auto_expand_accounts = True
        matrix = self.instance._compute_matrix()
        assert_matrix(matrix, [[11, 13], [11, 30]])

    def test_actuals_alt(self):
        aml_model = self.env["ir.model"].search([("name", "=", "account.move.line")])
        self.kpi2.auto_expand_accounts = False
        self.p1.source = SRC_ACTUALS_ALT
        self.p1.source_aml_model_id = aml_model.id
        self.p2.source = SRC_ACTUALS_ALT
        self.p1.source_aml_model_id = aml_model.id
        matrix = self.instance._compute_matrix()
        assert_matrix(matrix, [[11, 13], [11, 30]])
