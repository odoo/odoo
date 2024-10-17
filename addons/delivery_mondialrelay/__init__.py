# -*- coding: utf-8 -*-

from . import models
from . import wizard

from .models.delivery_carrier import DeliveryCarrier
from .models.res_partner import ResPartner
from .models.sale_order import SaleOrder
from .wizard.choose_delivery_carrier import ChooseDeliveryCarrier
