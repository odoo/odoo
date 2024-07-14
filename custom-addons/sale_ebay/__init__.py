# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import tools
from . import wizard

def uninstall_hook(env):
    icp = env['ir.config_parameter']
    # remove config parameter to ebay.site record
    icp.set_param('ebay_site', False)
    # remove config parameter to sale_ebay.ebay_sales_team
    team_id = int(icp.get_param('ebay_sales_team'))
    ebay_team = env.ref('sales_team.ebay_sales_team', False)
    if team_id and ebay_team and team_id == ebay_team.id:
        icp.set_param('ebay_sales_team', False)
