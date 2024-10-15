# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import pos_self_order


class ResConfigSettings(pos_self_order.ResConfigSettings):

    pos_self_order_online_payment_method_id = fields.Many2one(related='pos_config_id.self_order_online_payment_method_id', readonly=False)
