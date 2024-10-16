# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    CrmTeam, PosConfig, PosOrder, PosOrderLine, PosSession, ProductProduct,
    ResConfigSettings, SaleOrder, SaleOrderLine, StockPicking,
)
from .report import SaleReport


def _pos_sale_post_init(env):
    env['pos.config']._ensure_downpayment_product()
