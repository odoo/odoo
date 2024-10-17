# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.delivery_carrier import DeliveryCarrier
from .models.delivery_price_rule import DeliveryPriceRule
from .models.delivery_zip_prefix import DeliveryZipPrefix
from .models.product_category import ProductCategory
from .models.res_partner import ResPartner
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .wizard.choose_delivery_carrier import ChooseDeliveryCarrier
