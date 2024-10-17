# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.crm_lead import CrmLead
from .models.crm_team import CrmTeam
from .models.res_users import ResUsers
from .models.sale_order import SaleOrder
from .wizard.crm_opportunity_to_quotation import CrmQuotationPartner

def uninstall_hook(env):
    teams = env['crm.team'].search([('use_opportunities', '=', False)])
    teams.write({'use_opportunities': True})
