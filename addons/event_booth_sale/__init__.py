# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.account_move import AccountMove
from .models.event_booth import EventBooth
from .models.event_booth_category import EventBoothCategory
from .models.event_booth_registration import EventBoothRegistration
from .models.event_type_booth import EventTypeBooth
from .models.product_product import ProductProduct
from .models.product_template import ProductTemplate
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .wizard.event_booth_configurator import EventBoothConfigurator
