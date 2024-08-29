# -*- coding: utf-8 -*-
from odoo.addons import base

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    pos_crm_team_id = fields.Many2one(related='pos_config_id.crm_team_id', readonly=False, string='Sales Team (PoS)')
    pos_down_payment_product_id = fields.Many2one(related='pos_config_id.down_payment_product_id', readonly=False)
