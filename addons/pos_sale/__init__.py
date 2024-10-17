# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report

from .models.crm_team import CrmTeam
from .models.pos_config import PosConfig
from .models.pos_order import PosOrder, PosOrderLine
from .models.pos_session import PosSession
from .models.product_product import ProductProduct
from .models.res_config_settings import ResConfigSettings
from .models.sale_order import SaleOrder, SaleOrderLine
from .models.stock_picking import StockPicking
from .report.sale_report import SaleReport


def _pos_sale_post_init(env):
    env['pos.config']._ensure_downpayment_product()
