from . import controllers
from .models import (
    AccountFiscalPosition, IrBinary, IrHttp, PosCategory, PosConfig, PosLoadMixin,
    PosOrder, PosOrderLine, PosPaymentMethod, PosSession, Pos_Self_OrderCustom_Link,
    ProductProduct, ProductTemplate, ResConfigSettings, RestaurantFloor, RestaurantTable,
)


def _post_self_order_post_init(env):
    sessions = env['pos.session'].search([('state', '!=', 'closed')])
    if len(sessions) > 0:
        env['pos.session']._create_pos_self_sessions_sequence(sessions)
