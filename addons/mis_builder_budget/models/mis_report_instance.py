# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.osv.expression import AND

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator

from .mis_report_instance_period import SRC_MIS_BUDGET, SRC_MIS_BUDGET_BY_ACCOUNT


class MisBudgetAwareExpressionEvaluator(ExpressionEvaluator):
    def __init__(self, date_from, date_to, kpi_data, additional_move_line_filter):
        super().__init__(
            aep=None,
            date_from=date_from,
            date_to=date_to,
            additional_move_line_filter=additional_move_line_filter,
            aml_model=None,
        )
        self.kpi_data = kpi_data

    @api.model
    def _get_kpi_for_expressions(self, expressions):
        kpi = None
        for expression in expressions:
            if not expression:
                continue
            if kpi is None:
                kpi = expression.kpi_id
            else:
                assert (
                    kpi == expression.kpi_id
                ), "expressions must belong to the same kpi"
        return kpi

    def eval_expressions(self, expressions, locals_dict):
        kpi = self._get_kpi_for_expressions(expressions)
        if kpi and kpi.budgetable:
            vals = []
            drilldown_args = []
            for expression in expressions:
                vals.append(self.kpi_data.get(expression, AccountingNone))
                drilldown_args.append({"expr_id": expression.id})
            return vals, drilldown_args, False
        return super().eval_expressions(expressions, locals_dict)


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _add_column_mis_budget(self, aep, kpi_matrix, period, label, description):
        # fetch budget data for the period
        base_domain = AND(
            [
                [("budget_id", "=", period.source_mis_budget_id.id)],
                period._get_additional_budget_item_filter(),
            ]
        )
        kpi_data = self.env["mis.budget.item"]._query_kpi_data(
            period.date_from, period.date_to, base_domain
        )

        expression_evaluator = MisBudgetAwareExpressionEvaluator(
            period.date_from,
            period.date_to,
            kpi_data,
            period._get_additional_move_line_filter(),
        )
        return self.report_id._declare_and_compute_period(
            expression_evaluator,
            kpi_matrix,
            period.id,
            label,
            description,
            period.subkpi_ids,
            period._get_additional_query_filter,
            no_auto_expand_accounts=self.no_auto_expand_accounts,
        )

    def _add_column(self, aep, kpi_matrix, period, label, description):
        if period.source == SRC_MIS_BUDGET:
            return self._add_column_mis_budget(
                aep, kpi_matrix, period, label, description
            )
        elif period.source == SRC_MIS_BUDGET_BY_ACCOUNT:
            return self._add_column_move_lines(
                aep, kpi_matrix, period, label, description
            )
        else:
            return super()._add_column(aep, kpi_matrix, period, label, description)

    def drilldown(self, arg):
        self.ensure_one()
        period_id = arg.get("period_id")
        if period_id:
            period = self.env["mis.report.instance.period"].browse(period_id)
            if period.source == SRC_MIS_BUDGET:
                expr_id = arg.get("expr_id")
                if not expr_id:
                    return False
                domain = [
                    ("date_from", "<=", period.date_to),
                    ("date_to", ">=", period.date_from),
                    ("kpi_expression_id", "=", expr_id),
                    ("budget_id", "=", period.source_mis_budget_id.id),
                ]
                domain.extend(period._get_additional_budget_item_filter())
                return {
                    "name": period.name,
                    "domain": domain,
                    "type": "ir.actions.act_window",
                    "res_model": "mis.budget.item",
                    "views": [[False, "list"], [False, "form"]],
                    "view_mode": "list",
                    "target": "current",
                }
        return super().drilldown(arg)
