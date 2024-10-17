# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.sale_order import SaleOrder
from .wizard.sale_make_invoice_advance import SaleAdvancePaymentInv
