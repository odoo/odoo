# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .account_chart_template import AccountChartTemplate
from .account_move import AccountMove, AccountMoveLine
from .analytic_account import AccountAnalyticAccount, AccountAnalyticPlan
from .product import ProductCategory, ProductProduct, ProductTemplate
from .res_company import ResCompany
from .stock_move import StockMove
from .stock_location import StockLocation
from .stock_lot import StockLot
from .stock_move_line import StockMoveLine
from .stock_picking import StockPicking
from .stock_quant import StockQuant
from .stock_valuation_layer import StockValuationLayer
from .res_config_settings import ResConfigSettings
from . import template_generic_coa
