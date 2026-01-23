# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _load_self_data_models(self):
        return super()._load_self_data_models() + [
            'barcode.nomenclature',
            'barcode.rule',
            'loyalty.program',
            'loyalty.rule',
            'loyalty.reward',
            'loyalty.card'
        ]
