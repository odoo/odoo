from odoo import models, api


class PosPrepOrder(models.Model):
    _inherit = "pos.prep.order"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]


class PosPrepLine(models.Model):
    _inherit = "pos.prep.line"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]
