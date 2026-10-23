# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    @api.model
    def _load_pos_self_data_fields(self, config):
        return [field for field in super()._load_pos_self_data_fields(config) if field not in ('code', 'promo_barcode')]
