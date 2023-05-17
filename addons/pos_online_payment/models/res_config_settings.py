# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_online_payment_provider_ids = fields.Many2many(related='pos_config_id.online_payment_provider_ids', readonly=False)
