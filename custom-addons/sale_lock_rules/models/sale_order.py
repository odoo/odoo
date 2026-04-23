from odoo import models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        _logger.warning("ENTREI NO ACTION_CONFIRM")
        for order in self:
            if order.user_id.id == 2:
                raise UserError(
                    "Este vendedor não possui permissão para confirmar pedidos."
                )
        return super().action_confirm()
