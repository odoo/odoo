# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.route'

    routes_process_selection_types = fields.Selection([
        ('automation', 'Automation'),
        ('manual', 'Manual'),
        ('cross_dock', 'Cross Dock'),
        ('automation_bulk', 'Automation Bulk'),
        ('automation_putaway', 'Automation Putaway'),
    ], string='Process Type')
