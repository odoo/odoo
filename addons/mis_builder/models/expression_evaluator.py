# Copyright 2020 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from .mis_safe_eval import NameDataError, mis_safe_eval


class ExpressionEvaluator:
    def __init__(
        self,
        aep,
        date_from,
        date_to,
        additional_move_line_filter=None,
        aml_model=None,
    ):
        self.aep = aep
        self.date_from = date_from
        self.date_to = date_to
        self.additional_move_line_filter = additional_move_line_filter
        self.aml_model = aml_model
        self._aep_queries_done = False

    def aep_do_queries(self):
        if self.aep and not self._aep_queries_done:
            self.aep.do_queries(
                self.date_from,
                self.date_to,
                self.additional_move_line_filter,
                self.aml_model,
            )
            self._aep_queries_done = True

    def eval_expressions(self, expressions, locals_dict):
        vals = []
        drilldown_args = []
        name_error = False
        for expression in expressions:
            expr = expression and expression.name or "AccountingNone"
            if self.aep:
                replaced_expr = self.aep.replace_expr(expr)
            else:
                replaced_expr = expr
            val = mis_safe_eval(replaced_expr, locals_dict)
            vals.append(val)
            if isinstance(val, NameDataError):
                name_error = True
            if replaced_expr != expr:
                drilldown_args.append({"expr": expr})
            else:
                drilldown_args.append(None)
        return vals, drilldown_args, name_error

    def eval_expressions_by_account(self, expressions, locals_dict):
        if not self.aep:
            return
        exprs = [e and e.name or "AccountingNone" for e in expressions]
        for account_id, replaced_exprs in self.aep.replace_exprs_by_account_id(exprs):
            vals = []
            drilldown_args = []
            name_error = False
            for expr, replaced_expr in zip(exprs, replaced_exprs):  # noqa: B905
                val = mis_safe_eval(replaced_expr, locals_dict)
                vals.append(val)
                if replaced_expr != expr:
                    drilldown_args.append({"expr": expr, "account_id": account_id})
                else:
                    drilldown_args.append(None)
            yield account_id, vals, drilldown_args, name_error
