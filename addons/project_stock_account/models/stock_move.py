from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_analytic_distribution(self):
        _debug.logic("project_analytic_distribution", moves=self)
        if not self.picking_type_id.analytic_costs:
            return super()._get_analytic_distribution()
        distribution = self.picking_id.project_id._get_analytic_distribution()
        return distribution or super()._get_analytic_distribution()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(
            account_field_values, amount, unit_amount
        )
        if self.picking_id:
            res["name"] = self.picking_id.name
            res["category"] = "picking_entry"
        return res

    def _get_domain_valid_moves(self):
        _debug.logic("project_valid_moves_domain", moves=self)
        return [
            "&",
            ("picking_id.project_id", "!=", False),
            ("picking_type_id.analytic_costs", "!=", False),
        ]

    def _update_analytic_lines(self):
        _debug.pipeline("project_analytic_lines_prepare", moves=self)
        res = super()._update_analytic_lines()
        if res and self.picking_id:
            project = self.picking_id.project_id
            mandatory_plans = project._get_mandatory_plans(
                self.company_id, business_domain="stock_picking"
            )
            missing_plan_names = [
                plan["name"]
                for plan in mandatory_plans
                if not project[plan["column_name"]]
            ]
            if missing_plan_names:
                raise ValidationError(
                    _(
                        "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the stock picking.",
                        missing_plan_names=missing_plan_names,
                        project_name=project.name,
                    )
                )
        return res
