# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from .models.account_move import AccountMove, AccountMoveLine
from .models.analytic_account import AccountAnalyticAccount, AccountAnalyticPlan
from .models.product import ProductCategory, ProductProduct, ProductTemplate
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.stock_location import StockLocation
from .models.stock_lot import StockLot
from .models.stock_move import StockMove
from .models.stock_move_line import StockMoveLine
from .models.stock_picking import StockPicking
from .models.stock_quant import StockQuant
from .models.stock_valuation_layer import StockValuationLayer
from .models.template_generic_coa import AccountChartTemplate
from .report.stock_forecasted import StockForecasted_Product_Product
from .wizard.stock_picking_return import StockReturnPickingLine
from .wizard.stock_quantity_history import StockQuantityHistory
from .wizard.stock_request_count import StockRequestCount
from .wizard.stock_valuation_layer_revaluation import StockValuationLayerRevaluation


def _configure_journals(env):
    # if we already have a coa installed, create journal and set property field
    for company in env['res.company'].search([('chart_template', '!=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        template_code = company.chart_template
        full_data = ChartTemplate._get_chart_template_data(template_code)
        data = {
            'template_data': {
                fname: value
                for fname, value in full_data['template_data'].items()
                if fname in [
                    'property_stock_journal',
                    'property_stock_account_input_categ_id',
                    'property_stock_account_output_categ_id',
                    'property_stock_valuation_account_id',
                ]
            }
        }
        template_data = data.pop('template_data')
        journal = env['account.journal'].search([
            ('code', '=', 'STJ'),
            ('company_id', '=', company.id),
            ('type', '=', 'general')], limit=1)
        if journal:
            env['ir.model.data']._update_xmlids([{
                'xml_id': f"account.{company.id}_inventory_valuation",
                'record': journal,
                'noupdate': True,
            }])
        else:
            data['account.journal'] = ChartTemplate._get_stock_account_journal(template_code)
        ChartTemplate._load_data(data)
        ChartTemplate._post_load_data(template_code, company, template_data)
        ChartTemplate._load_wip_accounts(company, full_data['res.company'])
