# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    DeliveryCarrier, DeliveryPriceRule, DeliveryZipPrefix, ProductCategory,
    ResPartner, SaleOrder, SaleOrderLine,
)
from .wizard import ChooseDeliveryCarrier
