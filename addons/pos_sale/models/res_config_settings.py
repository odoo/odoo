# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_crm_team_id = fields.Many2one(related='pos_config_id.crm_team_id', related_inverse=True, string='Sales Team (PoS)')
    pos_down_payment_product_id = fields.Many2one(related='pos_config_id.down_payment_product_id', related_inverse=True)
