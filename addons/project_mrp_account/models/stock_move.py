from odoo import _, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_analytic_distribution(self):
        distribution = (
            self.raw_material_production_id.project_id._get_analytic_distribution()
        )
        return distribution or super()._get_analytic_distribution()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(
            account_field_values, amount, unit_amount
        )
        if self.raw_material_production_id:
            res["category"] = "manufacturing_order"
        return res

    def _update_analytic_lines(self):
        res = super()._update_analytic_lines()
        if res and self.raw_material_production_id:
            project = self.raw_material_production_id.project_id
            mandatory_plans = project._get_mandatory_plans(
                self.company_id, business_domain="manufacturing_order"
            )
            missing_plan_names = [
                plan["name"]
                for plan in mandatory_plans
                if not project[plan["column_name"]]
            ]
            if missing_plan_names:
                raise ValidationError(
                    _(
                        "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the manufacturing order.",
                        missing_plan_names=missing_plan_names,
                        project_name=project.name,
                    )
                )
        return res
