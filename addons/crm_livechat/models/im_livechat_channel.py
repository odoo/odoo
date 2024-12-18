# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Im_LivechatChannel(models.Model):
    _inherit = "im_livechat.channel"

    def _get_less_active_operator(self, operator_statuses, operators):
        if crm_team := self.env.context.get("crm_team_id"):
            team_operators = operators.filtered(lambda op: op in crm_team.crm_team_member_ids.user_id)
            operator = super()._get_less_active_operator(operator_statuses, team_operators)
            if operator:
                return operator
        return super()._get_less_active_operator(operator_statuses, operators)
