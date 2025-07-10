# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def _compute_dashboard_button_name(self):
        super(CrmTeam, self)._compute_dashboard_button_name()
        teams_with_opp = self.filtered(lambda team: team.use_opportunities)
        if self.env.context.get('in_sales_app'):
            teams_with_opp.update({'dashboard_button_name': _("Sales Analysis")})

    def action_primary_channel_button(self):
        if self.env.context.get('in_sales_app') and self.use_opportunities:
            return self.env["ir.actions.actions"]._for_xml_id("sale.action_order_report_so_salesteam")
        return super(CrmTeam,self).action_primary_channel_button()
