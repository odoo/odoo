# -*- coding: utf-8 -*-
from openerp import api, models


class PlannerCrm(models.Model):

    _inherit = 'web.planner'

    @api.model
    def _get_planner_application(self):
        planner = super(PlannerCrm, self)._get_planner_application()
        planner.append(['planner_crm', 'CRM Planner'])
        return planner

    @api.model
    def _prepare_planner_crm_data(self):
        # sudo is needed to avoid error message when current user's company != sale_department company
        sales_team = self.sudo().env.ref('sales_team.team_sales_department')
        values = {
            'alias_domain': sales_team.alias_domain,
            'alias_name': sales_team.alias_name,
            'pipeline_menu_id': self.env.ref('crm.menu_crm_opportunities').id,
        }
        return values
