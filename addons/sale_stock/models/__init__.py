# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .account_move import AccountMove, AccountMoveLine
from .product_template import ProductTemplate
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .res_users import ResUsers
from .sale_order import SaleOrder
from .sale_order_line import SaleOrderLine
from .stock import (
    ProcurementGroup, StockLot, StockMove, StockMoveLine, StockPicking, StockRoute,
    StockRule,
)
