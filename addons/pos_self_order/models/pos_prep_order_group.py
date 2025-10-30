from odoo import models, api


class PosPrepOrderGroup(models.Model):
    _inherit = "pos.prep.order.group"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]
