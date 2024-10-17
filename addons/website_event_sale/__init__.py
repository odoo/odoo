# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report

from .models.product import ProductProduct, ProductTemplate
from .models.product_pricelist import ProductPricelistItem
from .models.sale_order import SaleOrder, SaleOrderLine
from .report.event_sale_report import EventSaleReport
