from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _apply_hr_schedule_home_action(self):
        action = self.env.ref('hr_schedule_erp.hr_schedule_servicio_action', raise_if_not_found=False)
        if not action:
            return
        target_users = self.filtered(
            lambda user: not user.share
            and user.has_group('hr_schedule_erp.group_hr_programador_erp')
            and not user.action_id
        )
        if target_users:
            target_users.sudo().write({'action_id': action.id})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._apply_hr_schedule_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        # Si cambian grupos o si no tenía Home Action, intenta aplicarla
        if 'group_ids' in vals or 'action_id' not in vals:
            self._apply_hr_schedule_home_action()
        return res