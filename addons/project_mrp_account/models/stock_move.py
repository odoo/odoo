# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_analytic_distribution(self):
        distribution = self.raw_material_production_id.project_id._get_analytic_distribution()
        return distribution or super()._get_analytic_distribution()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        production = self.raw_material_production_id
        if production:
            res['category'] = 'manufacturing_order'
            if self.state == 'done' and production.state == 'done' and production.date_finished:
                res['date'] = fields.Date.context_today(production, timestamp=production.date_finished)
        if self.production_id:
            res.update({
                'name': self.env._("[EXTRA COST] %s", self.production_id.display_name),
                'ref': self.production_id.display_name,
                'product_uom_id': self.uom_id.id,
                'category': 'manufacturing_order',
            })
        return res

    def _prepare_analytic_lines(self):
        production = self.production_id
        if production and self.product_id == production.product_id:
            unit_amount = production.uom_id._compute_quantity(production.qty_producing, production.bom_id.uom_id, round=False) if self.state == 'done' else 0
            amount = -production.extra_cost * unit_amount
            distribution = production.project_id._get_analytic_distribution() if amount else {}
            res = self.env['account.analytic.account']._perform_analytic_distribution(
                distribution, amount, unit_amount, self.analytic_account_line_ids, self)
        else:
            res = super()._prepare_analytic_lines()
        production = self.raw_material_production_id or production
        if res and production:
            # Check that all mandatory plans are set on the project linked to the MO of the stock move before generating the AALs
            project = production.project_id
            mandatory_plans = project._get_mandatory_plans(self.company_id, business_domain='manufacturing_order')
            missing_plan_names = [plan['name'] for plan in mandatory_plans if not project[plan['column_name']]]
            if missing_plan_names:
                raise ValidationError(_(
                    "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the manufacturing order.",
                    missing_plan_names=missing_plan_names,
                    project_name=project.name,
                ))
        return res
