from odoo import models, fields, api, tools
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        print('hereeeeeeeeeeeeee')
        result = super().sync_from_ui( orders)
        print('result',result)
        return result