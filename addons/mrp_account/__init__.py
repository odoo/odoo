# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import report
from . import wizard

from .models.account_move import AccountMove, AccountMoveLine
from .models.analytic_account import (
    AccountAnalyticAccount, AccountAnalyticApplicability,
    AccountAnalyticLine,
)
from .models.mrp_production import MrpProduction
from .models.mrp_routing import MrpRoutingWorkcenter
from .models.mrp_workcenter import MrpWorkcenter, MrpWorkcenterProductivity
from .models.mrp_workorder import MrpWorkorder
from .models.product import ProductCategory, ProductProduct, ProductTemplate
from .models.stock_move import StockMove
from .report.mrp_report_mo_overview import ReportMrpReport_Mo_Overview
from .wizard.mrp_wip_accounting import MrpAccountWipAccounting, MrpAccountWipAccountingLine


def _configure_journals(env):
    # if we already have a coa installed, create journal and set property field
    for company in env['res.company'].search([('chart_template', '!=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        template_data = ChartTemplate._get_chart_template_data(template_code)['template_data']
        if 'property_stock_account_production_cost_id' in template_data:
            data = {'property_stock_account_production_cost_id': template_data['property_stock_account_production_cost_id']}
            ChartTemplate._post_load_data(template_code, company, data)
