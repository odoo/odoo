# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import stock

from odoo import fields, models


class StockPicking(models.Model, stock.StockPicking):

    zip = fields.Char(related='partner_id.zip', string='Zip', search="_search_zip")

    def _search_zip(self, operator, value):
        return [('partner_id.zip', operator, value)]
