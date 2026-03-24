from odoo import _, api, models
from odoo.addons.mail.tools.discuss import Store


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

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        res.attr("has_access_create_lead", self.has_group("sales_team.group_sale_salesman"))
        res.attr(
            "channel_types_with_create_lead",
            sorted(self.env["discuss.channel"]._types_allowing_create_lead()),
        )
