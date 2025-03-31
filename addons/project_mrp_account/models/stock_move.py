# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.tools import format_list


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_analytic_distribution(self):
        distribution = self.raw_material_production_id.project_id._get_analytic_distribution()
        return distribution or super()._get_analytic_distribution()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        if self.raw_material_production_id:
            res['category'] = 'manufacturing_order'
        return res

    def _prepare_analytic_lines(self):
        res = super()._prepare_analytic_lines()
        if res and self.raw_material_production_id:
            # Check that all mandatory plans are set on the project linked to the MO of the stock move before generating the AALs
            project = self.raw_material_production_id.project_id
            mandatory_plans = project._get_mandatory_plans(self.company_id, business_domain='manufacturing_order')
            missing_plan_names = [plan['name'] for plan in mandatory_plans if not project[plan['column_name']]]
            if missing_plan_names:
                raise ValidationError(_(
                    "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the manufacturing order.",
                    missing_plan_names=format_list(self.env, missing_plan_names),
                    project_name=project.name,
                ))
        return res
