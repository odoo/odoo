# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report

from .models.lunch_alert import LunchAlert
from .models.lunch_cashmove import LunchCashmove
from .models.lunch_location import LunchLocation
from .models.lunch_order import LunchOrder
from .models.lunch_product import LunchProduct
from .models.lunch_product_category import LunchProductCategory
from .models.lunch_supplier import LunchSupplier
from .models.lunch_topping import LunchTopping
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_users import ResUsers
from .report.lunch_cashmove_report import LunchCashmoveReport
