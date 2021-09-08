# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)
    
class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', related='')
