# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .models import (
    AccountAnalyticAccount, AccountAnalyticApplicability, AccountAnalyticLine,
    AccountMove, AccountMoveLine, MrpProduction, MrpRoutingWorkcenter, MrpWorkcenter,
    MrpWorkcenterProductivity, MrpWorkorder, ProductCategory, ProductProduct, ProductTemplate,
    StockMove,
)
from .report import ReportMrpReport_Mo_Overview
from .wizard import MrpAccountWipAccounting, MrpAccountWipAccountingLine


def _configure_journals(env):
    # if we already have a coa installed, create journal and set property field
    for company in env['res.company'].search([('chart_template', '!=', False)], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        template_data = ChartTemplate._get_chart_template_data(template_code)['template_data']
        if 'property_stock_account_production_cost_id' in template_data:
            data = {'property_stock_account_production_cost_id': template_data['property_stock_account_production_cost_id']}
            ChartTemplate._post_load_data(template_code, company, data)
