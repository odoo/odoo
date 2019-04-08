# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    teams = env['crm.team'].search([('dashboard_graph_model', '=', 'crm.opportunity.report')])
    teams.update({'dashboard_graph_model': None})

def _update_sale_teams(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    sale_team = env.ref('sales_team.team_sales_department', False)
    ws_team = env.ref('sales_team.salesteam_website_sales', False)
    teams = [team for team in [sale_team, ws_team] if team]

    if teams:
        env['crm.team'].message_unsubscribe(teams, [env.ref('base.partner_root')])
        env['crm.team'].message_subscribe(teams, [env.ref('base.partner_root')])

    if sale_team:
        sale_team.write({
            'use_opportunities': True,
            'alias_name': 'sales',
            'dashboard_graph_model': 'crm.lead',
        })
