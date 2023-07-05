# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_pay_after = fields.Selection(selection_add=[("meal", "Meal")], ondelete={'meal': lambda recs: recs.write({'pos_self_order_pay_after': 'each'})})
