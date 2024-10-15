# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons import point_of_sale


class PosSession(point_of_sale.PosSession):

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data
