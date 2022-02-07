# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_coupon_program_ids = fields.Many2many(related='pos_config_id.coupon_program_ids', readonly=False)
    pos_promo_program_ids = fields.Many2many(related='pos_config_id.promo_program_ids', readonly=False)
