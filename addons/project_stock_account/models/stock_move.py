# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import OR
from odoo.tools import format_list


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_analytic_distribution(self):
        if not self.picking_type_id.analytic_costs:
            return super()._get_analytic_distribution()
        distribution = self.picking_id.project_id._get_analytic_distribution()
        return distribution or super()._get_analytic_distribution()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        res = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        if self.picking_id:
            res['name'] = self.picking_id.name
            res['category'] = 'picking_entry'
        return res

    def _get_valid_moves_domain(self):
        return ['&', ('picking_id.project_id', '!=', False), ('picking_type_id.analytic_costs', '!=', False)]

    def _account_analytic_entry_move(self):
        domain = self._get_valid_moves_domain()
        domain = OR([[('picking_id', '=', False)], domain])
        valid_moves = self.filtered_domain(domain)
        super(StockMove, valid_moves)._account_analytic_entry_move()

    def _prepare_analytic_lines(self):
        res = super()._prepare_analytic_lines()
        if res and self.picking_id:
            # Check that all mandatory plans are set on the project linked to the picking of the stock move before generating the AALs
            project = self.picking_id.project_id
            mandatory_plans = project._get_mandatory_plans(self.company_id, business_domain='stock_picking')
            missing_plan_names = [plan['name'] for plan in mandatory_plans if not project[plan['column_name']]]
            if missing_plan_names:
                raise ValidationError(_(
                    "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the stock picking.",
                    missing_plan_names=format_list(self.env, missing_plan_names),
                    project_name=project.name,
                ))
        return res
