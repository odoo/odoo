# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID, Command

from .models.product_product import ProductProduct, ProductTemplate
from .models.production_lot import ProcurementGroup, StockLot
from .models.res_config_settings import ResConfigSettings
from .models.stock_move import StockMove
from .models.stock_move_line import StockMoveLine
from .models.stock_picking import StockPicking
from .models.stock_quant import StockQuant
from .wizard.confirm_expiry import ExpiryPickingConfirmation

def _enable_tracking_numbers(env):
    """ This hook ensures the tracking numbers are enabled when the module is installed since the
    user can install `product_expiry` manually without enable `group_production_lot`.
    """
    group_production_lot = env.ref('stock.group_production_lot')
    groups = env.ref('base.group_user') + env.ref('base.group_portal')
    groups.write({'implied_ids': [Command.link(group_production_lot.id)]})
