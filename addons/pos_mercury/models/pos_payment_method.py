# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['pos_mercury_config_id']
        return params
