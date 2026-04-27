# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_plan_users_ids = fields.One2many('sale.commission.plan.user', 'user_id', 'Commission plans')
    filtered_commission_plan_users_ids = fields.One2many('sale.commission.plan.user', compute='_compute_filtered_commission_plan_users_ids')

    def write(self, values):
        res = super().write(values)
        if 'sale_team_id' in values:
            today = fields.Date.today()
            commission_plan_user = [{
                'plan_id': plan.id,
                'user_id': user.id,
                'team_id': user.sale_team_id.id,
            } for user in self for plan in user.sale_team_id.commission_plan_ids if plan.date_to <= today]
            self.env['sale.commission.plan.user'].create(commission_plan_user)
        return res

    @api.depends('commission_plan_users_ids')
    def _compute_filtered_commission_plan_users_ids(self):
        today = fields.Date.today()
        for user in self:
            user.filtered_commission_plan_users_ids = user.commission_plan_users_ids.filtered(lambda x:
                x.date_from >= today and x.date_to <= today)
