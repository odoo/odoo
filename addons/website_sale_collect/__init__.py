# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import utils

from odoo.addons.payment import reset_payment_provider

from .models.delivery_carrier import DeliveryCarrier
from .models.payment_provider import PaymentProvider
from .models.product_template import ProductTemplate
from .models.res_config_settings import ResConfigSettings
from .models.sale_order import SaleOrder
from .models.stock_warehouse import StockWarehouse
from .models.website import Website


def uninstall_hook(env):
    reset_payment_provider(env, 'custom', custom_mode='on_site')
