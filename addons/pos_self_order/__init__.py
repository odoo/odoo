from . import controllers
from . import models

from .models.account_fiscal_position import AccountFiscalPosition
from .models.ir_binary import IrBinary
from .models.ir_http import IrHttp
from .models.pos_category import PosCategory
from .models.pos_config import PosConfig
from .models.pos_load_mixin import PosLoadMixin
from .models.pos_order import PosOrder, PosOrderLine
from .models.pos_payment_method import PosPaymentMethod
from .models.pos_restaurant import RestaurantFloor, RestaurantTable
from .models.pos_self_order_custom_link import Pos_Self_OrderCustom_Link
from .models.pos_session import PosSession
from .models.product_product import ProductProduct, ProductTemplate
from .models.res_config_settings import ResConfigSettings


def _post_self_order_post_init(env):
    sessions = env['pos.session'].search([('state', '!=', 'closed')])
    if len(sessions) > 0:
        env['pos.session']._create_pos_self_sessions_sequence(sessions)
