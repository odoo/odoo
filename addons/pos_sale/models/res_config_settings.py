# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import point_of_sale, sale_management


class ResConfigSettings(point_of_sale.ResConfigSettings, sale_management.ResConfigSettings):

    pos_crm_team_id = fields.Many2one(related='pos_config_id.crm_team_id', readonly=False, string='Sales Team (PoS)')
    pos_down_payment_product_id = fields.Many2one(related='pos_config_id.down_payment_product_id', readonly=False)
