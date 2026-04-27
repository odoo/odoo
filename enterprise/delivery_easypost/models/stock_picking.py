# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ep_order_ref = fields.Char("Easypost Order Reference", copy=False)
