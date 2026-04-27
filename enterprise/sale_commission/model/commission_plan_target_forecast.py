# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CommissionPlanTargetForecast(models.Model):
    _name = 'sale.commission.plan.target.forecast'
    _description = 'Commission Plan Target Forecast'
    _order = 'id'

    plan_id = fields.Many2one('sale.commission.plan', ondelete='cascade')
    target_id = fields.Many2one('sale.commission.plan.target', string="Period", required=True, ondelete='cascade',
                                domain="[('plan_id', '=', plan_id)]")
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', related='user_id.sale_team_id', depends=['user_id'], store=True)
    amount = fields.Monetary("Forecast", default=0, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='plan_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        user_ids = [vals.get('user_id') for vals in vals_list]
        plan_ids = [vals.get('plan_id') for vals in vals_list]
        existing_plan_user = self.env['sale.commission.plan.user'].read_group(
            [('user_id', 'in', user_ids), ('plan_id', 'in', plan_ids)],
            ['plan_id:array_agg'],
            ['user_id'],
        )
        existing_plan_user = {group['user_id'][0]: group['plan_id'] for group in existing_plan_user}
        for vals in vals_list:
            if not vals.get('plan_id') in existing_plan_user.get(vals.get('user_id'), {}):
                raise ValidationError(_('You cannot create a forecast for an user that is not in the plan.'))
        return super().create(vals_list)
