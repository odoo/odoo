# -*- coding: utf-8 -*-

from . import product
from . import res_country
from . import res_currency
from . import res_partner
from . import sale_ebay
# Needs to be after sale_ebay,
# because the default of the field `ebay_site` requires the model `ebay.site` to be installed.
from . import sale_order
from . import res_config_settings
from . import stock_picking
