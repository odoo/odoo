# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models      # noqa
from . import report      # noqa

from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .report.sale_report import SaleReport
