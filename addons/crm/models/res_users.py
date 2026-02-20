from odoo import _, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.depends_context(
        'crm_formatted_display_name_team',
        'formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        formatted_display_name = self.env.context.get('formatted_display_name')
        team_id = self.env.context.get('crm_formatted_display_name_team', 0)
        if formatted_display_name and team_id:
            leader_id = self.env['crm.team'].browse(team_id).user_id
            for user in self.filtered(lambda u: u == leader_id):
                user.display_name += " --%s--" % _("(Team Leader)")

    @api.depends('crm_team_member_ids.crm_team_id', 'crm_team_member_ids.create_date', 'crm_team_member_ids.active')
    def _compute_sale_team_id(self):
        # Only recompute when the team is not set or invalid
        users = self.filtered(lambda user: not user.sale_team_id or user.sale_team_id not in user.crm_team_ids)
        super(ResUsers, users)._compute_sale_team_id()
