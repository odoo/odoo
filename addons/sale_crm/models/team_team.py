from odoo import _, models


class TeamTeam(models.Model):
    _inherit = "team.team"

    def _compute_dashboard_button_name(self):
        super()._compute_dashboard_button_name()
        teams_with_opp = self.filtered(lambda team: team.use_opportunities)
        if self.env.context.get("in_sales_app"):
            teams_with_opp.update({"dashboard_button_name": _("Sales Analysis")})

    def action_primary_channel_button(self):
        if self.env.context.get("in_sales_app") and self.use_opportunities:
            return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "sale_team.action_sale_report_so_salesteam"
            )
        return super().action_primary_channel_button()
