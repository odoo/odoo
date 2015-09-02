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
        menu = self.env.ref('crm.menu_crm_opportunities', raise_if_not_found=False)
        # sudo is needed to avoid error message when current user's company != sale_department company
        sales_team = self.sudo().env.ref('sales_team.team_sales_department', raise_if_not_found=False)
        return {
            'alias_domain': sales_team and sales_team.alias_domain or False,
            'alias_name': sales_team and sales_team.alias_name or False,
            'pipeline_menu_id': menu and menu.id or False
        }
