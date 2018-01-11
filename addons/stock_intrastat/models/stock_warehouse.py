# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    region_id = fields.Many2one('account.intrastat.region', string='Intrastat region')
