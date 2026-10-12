# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    has_analytic_account = fields.Boolean(compute='_compute_has_analytic_account')

    @api.depends('project_id')
    def _compute_has_analytic_account(self):
        has_analytic_account_per_project_id = {p.id: bool(p._get_analytic_accounts()) for p in self.project_id}
        for production in self:
            production.has_analytic_account = has_analytic_account_per_project_id.get(production.project_id.id, False)

    def action_view_analytic_accounts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'domain': [('id', 'in', self.project_id._get_analytic_accounts().ids)],
            'name': _('Analytic Accounts'),
            'view_mode': 'list,form',
        }

    def write(self, vals):
        res = super().write(vals)
        for production in self:
            if 'project_id' in vals and production.state != 'draft':
                production.move_raw_ids._create_analytic_move()
                production.workorder_ids._create_or_update_analytic_entry()
        return res

    def _validate_analytic_distribution(self):
        for production in self:
            # Pass the produced product so applicabilities filtered by product_categ_id
            plans = self.env['account.analytic.plan'].sudo().with_company(production.company_id).get_relevant_plans(
                business_domain='manufacturing_order',
                company_id=production.company_id.id,
                product=production.product_id.id,
            )
            missing_plan_names = [
                plan['name'] for plan in plans
                if plan['applicability'] == 'mandatory' and not production.project_id[plan['column_name']]
            ]
            if missing_plan_names:
                raise ValidationError(_(
                    "The Project linked to the Manufacturing Order is missing a mandatory distribution for the analytic plan(s) %(missing_plan_names)s.",
                    missing_plan_names=', '.join(missing_plan_names),
                ))

    def action_confirm(self):
        self._validate_analytic_distribution()
        return super().action_confirm()
