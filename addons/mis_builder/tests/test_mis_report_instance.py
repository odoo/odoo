# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common
from odoo.tools import test_reports

from ..models.accounting_none import AccountingNone
from ..models.mis_report import TYPE_STR, SubKPITupleLengthError, SubKPIUnknownTypeError


class TestMisReportInstance(common.HttpCase):
    """Basic integration test to exercise mis.report.instance.

    We don't check the actual results here too much as computation correctness
    should be covered by lower level unit tests.
    """

    def setUp(self):
        super().setUp()
        partner_model_id = self.env.ref("base.model_res_partner").id
        partner_create_date_field_id = self.env.ref(
            "base.field_res_partner__create_date"
        ).id
        partner_debit_field_id = self.env.ref("account.field_res_partner__debit").id
        # create a report with 2 subkpis and one query
        self.report = self.env["mis.report"].create(
            dict(
                name="test report",
                subkpi_ids=[
                    (0, 0, dict(name="sk1", description="subkpi 1", sequence=1)),
                    (0, 0, dict(name="sk2", description="subkpi 2", sequence=2)),
                ],
                query_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="partner",
                            model_id=partner_model_id,
                            field_ids=[(4, partner_debit_field_id, None)],
                            date_field=partner_create_date_field_id,
                            aggregate="sum",
                        ),
                    )
                ],
            )
        )
        # create another report with 2 subkpis, no query
        self.report_2 = self.env["mis.report"].create(
            dict(
                name="another test report",
                subkpi_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="subkpi1_report2",
                            description="subkpi 1, report 2",
                            sequence=1,
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="subkpi2_report2",
                            description="subkpi 2, report 2",
                            sequence=2,
                        ),
                    ),
                ],
            )
        )
        # Third report, 2 subkpis, no query
        self.report_3 = self.env["mis.report"].create(
            dict(
                name="test report 3",
                subkpi_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="subkpi1_report3",
                            description="subkpi 1, report 3",
                            sequence=1,
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="subkpi2_report3",
                            description="subkpi 2, report 3",
                            sequence=2,
                        ),
                    ),
                ],
            )
        )
        # kpi with accounting formulas
        self.kpi1 = self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 1",
                name="k1",
                multi=True,
                expression_ids=[
                    (
                        0,
                        0,
                        dict(name="bale[200%]", subkpi_id=self.report.subkpi_ids[0].id),
                    ),
                    (
                        0,
                        0,
                        dict(name="balp[200%]", subkpi_id=self.report.subkpi_ids[1].id),
                    ),
                ],
            )
        )
        # kpi with accounting formula and query
        self.kpi2 = self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 2",
                name="k2",
                multi=True,
                expression_ids=[
                    (
                        0,
                        0,
                        dict(name="balp[200%]", subkpi_id=self.report.subkpi_ids[0].id),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="partner.debit", subkpi_id=self.report.subkpi_ids[1].id
                        ),
                    ),
                ],
            )
        )
        # kpi with a simple expression summing other multi-valued kpis
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 4",
                name="k4",
                multi=False,
                expression="k1 + k2 + k3",
            )
        )
        # kpi with 2 constants
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 3",
                name="k3",
                multi=True,
                expression_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="AccountingNone",
                            subkpi_id=self.report.subkpi_ids[0].id,
                        ),
                    ),
                    (0, 0, dict(name="1.0", subkpi_id=self.report.subkpi_ids[1].id)),
                ],
            )
        )
        # kpi with a NameError (x not defined)
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 5",
                name="k5",
                multi=True,
                expression_ids=[
                    (0, 0, dict(name="x", subkpi_id=self.report.subkpi_ids[0].id)),
                    (0, 0, dict(name="1.0", subkpi_id=self.report.subkpi_ids[1].id)),
                ],
            )
        )
        # string-type kpi
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 6",
                name="k6",
                multi=True,
                type=TYPE_STR,
                expression_ids=[
                    (0, 0, dict(name='"bla"', subkpi_id=self.report.subkpi_ids[0].id)),
                    (
                        0,
                        0,
                        dict(name='"blabla"', subkpi_id=self.report.subkpi_ids[1].id),
                    ),
                ],
            )
        )
        # kpi that references another subkpi by name
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                description="kpi 7",
                name="k7",
                multi=True,
                expression_ids=[
                    (0, 0, dict(name="k3.sk1", subkpi_id=self.report.subkpi_ids[0].id)),
                    (0, 0, dict(name="k3.sk2", subkpi_id=self.report.subkpi_ids[1].id)),
                ],
            )
        )
        # Report 2 : kpi with AccountingNone value
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report_2.id,
                description="AccountingNone kpi",
                name="AccountingNoneKPI",
                multi=False,
            )
        )
        # Report 2 : 'classic' kpi with values for each sub-KPI
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report_2.id,
                description="Classic kpi",
                name="classic_kpi_r2",
                multi=True,
                expression_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="bale[200%]", subkpi_id=self.report_2.subkpi_ids[0].id
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="balp[200%]", subkpi_id=self.report_2.subkpi_ids[1].id
                        ),
                    ),
                ],
            )
        )
        # Report 3 : kpi with wrong tuple length
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report_3.id,
                description="Wrong tuple length kpi",
                name="wrongTupleLen",
                multi=False,
                expression="('hello', 'does', 'this', 'work')",
            )
        )
        # Report 3 : 'classic' kpi
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report_3.id,
                description="Classic kpi",
                name="classic_kpi_r2",
                multi=True,
                expression_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="bale[200%]", subkpi_id=self.report_3.subkpi_ids[0].id
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="balp[200%]", subkpi_id=self.report_3.subkpi_ids[1].id
                        ),
                    ),
                ],
            )
        )
        # create a report instance
        self.report_instance = self.env["mis.report.instance"].create(
            dict(
                name="test instance",
                report_id=self.report.id,
                company_id=self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="p1",
                            mode="relative",
                            type="d",
                            subkpi_ids=[(4, self.report.subkpi_ids[0].id, None)],
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            name="p2",
                            mode="fix",
                            manual_date_from="2014-01-01",
                            manual_date_to="2014-12-31",
                        ),
                    ),
                ],
            )
        )
        # same for report 2
        self.report_instance_2 = self.env["mis.report.instance"].create(
            dict(
                name="test instance 2",
                report_id=self.report_2.id,
                company_id=self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="p3",
                            mode="fix",
                            manual_date_from="2019-01-01",
                            manual_date_to="2019-12-31",
                        ),
                    )
                ],
            )
        )
        # and for report 3
        self.report_instance_3 = self.env["mis.report.instance"].create(
            dict(
                name="test instance 3",
                report_id=self.report_3.id,
                company_id=self.env.ref("base.main_company").id,
                period_ids=[
                    (
                        0,
                        0,
                        dict(
                            name="p4",
                            mode="fix",
                            manual_date_from="2019-01-01",
                            manual_date_to="2019-12-31",
                        ),
                    )
                ],
            )
        )

    def test_compute(self):
        matrix = self.report_instance._compute_matrix()
        for row in matrix.iter_rows():
            vals = [c.val for c in row.iter_cells()]
            if row.kpi.name == "k3":
                # k3 is constant
                self.assertEqual(vals, [AccountingNone, AccountingNone, 1.0])
            elif row.kpi.name == "k6":
                # k6 is a string kpi
                self.assertEqual(vals, ["bla", "bla", "blabla"])
            elif row.kpi.name == "k7":
                # k7 references k3 via subkpi names
                self.assertEqual(vals, [AccountingNone, AccountingNone, 1.0])

    def test_multi_company_compute(self):
        self.report_instance.write(
            {
                "multi_company": True,
                "company_ids": [(6, 0, self.report_instance.company_id.ids)],
            }
        )
        self.report_instance.report_id.kpi_ids.write({"auto_expand_accounts": True})
        matrix = self.report_instance._compute_matrix()
        for row in matrix.iter_rows():
            if row.account_id:
                account = self.env["account.account"].browse(row.account_id)
                self.assertEqual(
                    row.label,
                    f"{account.code} {account.name} [{account.company_id.name}]",
                )
        self.report_instance.write({"multi_company": False})
        matrix = self.report_instance._compute_matrix()
        for row in matrix.iter_rows():
            if row.account_id:
                account = self.env["account.account"].browse(row.account_id)
                self.assertEqual(row.label, f"{account.code} {account.name}")

    def test_evaluate(self):
        company = self.env.ref("base.main_company")
        aep = self.report._prepare_aep(company)
        r = self.report.evaluate(aep, date_from="2014-01-01", date_to="2014-12-31")
        self.assertEqual(r["k3"], (AccountingNone, 1.0))
        self.assertEqual(r["k6"], ("bla", "blabla"))
        self.assertEqual(r["k7"], (AccountingNone, 1.0))

    def test_json(self):
        self.report_instance.compute()

    def test_drilldown(self):
        action = self.report_instance.drilldown(
            dict(expr="balp[200%]", period_id=self.report_instance.period_ids[0].id)
        )
        account_ids = (
            self.env["account.account"]
            .search(
                [
                    ("code", "=like", "200%"),
                    ("company_id", "=", self.env.ref("base.main_company").id),
                ]
            )
            .ids
        )
        self.assertTrue(("account_id", "in", tuple(account_ids)) in action["domain"])
        self.assertEqual(action["res_model"], "account.move.line")

    def test_drilldown_action_name_with_account(self):
        period = self.report_instance.period_ids[0]
        account = self.env["account.account"].search([], limit=1)
        args = {
            "period_id": period.id,
            "kpi_id": self.kpi1.id,
            "account_id": account.id,
        }
        action_name = self.report_instance._get_drilldown_action_name(args)
        expected_name = "{kpi} - {account} - {period}".format(
            kpi=self.kpi1.description,
            account=account.display_name,
            period=period.display_name,
        )
        assert action_name == expected_name

    def test_drilldown_action_name_without_account(self):
        period = self.report_instance.period_ids[0]
        args = {
            "period_id": period.id,
            "kpi_id": self.kpi1.id,
        }
        action_name = self.report_instance._get_drilldown_action_name(args)
        expected_name = f"{self.kpi1.description} - {period.display_name}"
        assert action_name == expected_name

    def test_drilldown_views(self):
        IrUiView = self.env["ir.ui.view"]
        model_name = "account.move.line"
        IrUiView.search([("model", "=", model_name)]).unlink()
        IrUiView.create(
            [
                {
                    "name": "mis_report_test_drilldown_views_chart",
                    "model": model_name,
                    "arch": "<graph><field name='name'/></graph>",
                },
                {
                    "name": "mis_report_test_drilldown_views_tree",
                    "model": model_name,
                    "arch": "<pivot><field name='name'/></pivot>",
                },
            ]
        )
        action = self.report_instance.drilldown(
            dict(expr="balp[200%]", period_id=self.report_instance.period_ids[0].id)
        )
        self.assertEqual(action["view_mode"], "pivot,graph")
        self.assertEqual(action["views"], [[False, "pivot"], [False, "graph"]])
        IrUiView.create(
            [
                {
                    "name": "mis_report_test_drilldown_views_form",
                    "model": model_name,
                    "arch": "<form><field name='name'/></form>",
                },
                {
                    "name": "mis_report_test_drilldown_views_tree",
                    "model": model_name,
                    "arch": "<tree><field name='name'/></tree>",
                },
            ]
        )
        action = self.report_instance.drilldown(
            dict(expr="balp[200%]", period_id=self.report_instance.period_ids[0].id)
        )
        self.assertEqual(action["view_mode"], "tree,form,pivot,graph")
        self.assertEqual(
            action["views"],
            [[False, "tree"], [False, "form"], [False, "pivot"], [False, "graph"]],
        )

    def test_qweb(self):
        self.report_instance.print_pdf()  # get action
        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            "mis_builder.report_mis_report_instance",
            [self.report_instance.id],
            report_type="qweb-pdf",
        )

    def test_xlsx(self):
        self.report_instance.export_xls()  # get action
        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            "mis_builder.mis_report_instance_xlsx",
            [self.report_instance.id],
            report_type="xlsx",
        )

    def test_get_kpis_by_account_id(self):
        account_ids = (
            self.env["account.account"]
            .search(
                [
                    ("code", "=like", "200%"),
                    ("company_id", "=", self.env.ref("base.main_company").id),
                ]
            )
            .ids
        )
        kpi200 = {self.kpi1, self.kpi2}
        res = self.report.get_kpis_by_account_id(self.env.ref("base.main_company"))
        for account_id in account_ids:
            self.assertTrue(account_id in res)
            self.assertEqual(res[account_id], kpi200)

    def test_kpi_name_get_name_search(self):
        r = self.env["mis.report.kpi"].name_search("k1")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][0], self.kpi1.id)
        self.assertEqual(r[0][1], "kpi 1 (k1)")
        r = self.env["mis.report.kpi"].name_search("kpi 1")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][0], self.kpi1.id)
        self.assertEqual(r[0][1], "kpi 1 (k1)")

    def test_kpi_expr_name_get_name_search(self):
        r = self.env["mis.report.kpi.expression"].name_search("k1")
        self.assertEqual(
            [i[1] for i in r],
            ["kpi 1 / subkpi 1 (k1.sk1)", "kpi 1 / subkpi 2 (k1.sk2)"],
        )
        r = self.env["mis.report.kpi.expression"].name_search("k1.sk1")
        self.assertEqual([i[1] for i in r], ["kpi 1 / subkpi 1 (k1.sk1)"])
        r = self.env["mis.report.kpi.expression"].name_search("k4")
        self.assertEqual([i[1] for i in r], ["kpi 4 (k4)"])

    def test_query_company_ids(self):
        # sanity check single company mode
        assert not self.report_instance.multi_company
        assert self.report_instance.company_id
        assert self.report_instance.query_company_ids == self.report_instance.company_id
        # create a second company
        c1 = self.report_instance.company_id
        c2 = self.env["res.company"].create(
            dict(
                name="company 2",
            )
        )
        self.report_instance.write(dict(multi_company=True, company_id=False))
        self.report_instance.company_ids |= c1
        self.report_instance.company_ids |= c2
        assert len(self.report_instance.company_ids) == 2
        self.assertFalse(self.report_instance.query_company_ids - self.env.companies)
        # In a user context where there is only one company, ensure
        # query_company_ids only has one company too.
        assert (
            self.report_instance.with_context(
                allowed_company_ids=(c1.id,)
            ).query_company_ids
            == c1
        )

    def test_multi_company_onchange(self):
        # not multi company
        self.assertTrue(self.report_instance.company_id)
        self.assertFalse(self.report_instance.multi_company)
        self.assertFalse(self.report_instance.company_ids)
        self.assertEqual(
            self.report_instance.query_company_ids[0], self.report_instance.company_id
        )
        # create a child company
        self.env["res.company"].create(
            dict(name="company 2", parent_id=self.report_instance.company_id.id)
        )
        self.report_instance.multi_company = True
        # multi company, company_ids not set
        self.assertEqual(self.report_instance.query_company_ids, self.env.companies)
        # set company_ids
        previous_company = self.report_instance.company_id
        self.report_instance._onchange_company()
        self.assertFalse(self.report_instance.company_id)
        self.assertTrue(self.report_instance.multi_company)
        self.assertEqual(self.report_instance.company_ids, previous_company)
        self.assertEqual(self.report_instance.query_company_ids, previous_company)
        # reset single company mode
        self.report_instance.multi_company = False
        self.report_instance._onchange_company()
        self.assertEqual(
            self.report_instance.query_company_ids[0], self.report_instance.company_id
        )
        self.assertFalse(self.report_instance.company_ids)

    def test_mis_report_analytic_filters(self):
        # Check that matrix has no values when using a filter with a non existing value
        matrix = self.report_instance.with_context(
            analytic_domain=[("partner_id", "=", -1)]
        )._compute_matrix()
        for row in matrix.iter_rows():
            vals = [c.val for c in row.iter_cells()]
            if row.kpi.name == "k1":
                self.assertEqual(vals, [AccountingNone, AccountingNone, AccountingNone])
            elif row.kpi.name == "k2":
                self.assertEqual(vals, [AccountingNone, AccountingNone, None])
            elif row.kpi.name == "k4":
                self.assertEqual(vals, [AccountingNone, AccountingNone, 1.0])

    def test_raise_when_unknown_kpi_value_type(self):
        with self.assertRaises(SubKPIUnknownTypeError):
            self.report_instance_2.compute()

    def test_raise_when_wrong_tuple_length_with_subkpis(self):
        with self.assertRaises(SubKPITupleLengthError):
            self.report_instance_3.compute()

    def test_unprivileged(self):
        test_user = common.new_test_user(
            self.env, "mis_you", groups="base.group_user,account.group_account_readonly"
        )
        self.report_instance.with_user(test_user).compute()
