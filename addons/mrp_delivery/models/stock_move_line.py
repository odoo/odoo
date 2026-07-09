# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
