# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_sequence_stage_ids = fields.Many2many('pos.sequence.stage', string='Sequence Stages', help='The stages that this product can be in the kitchen order sequence.')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['pos_sequence_stage_ids']
