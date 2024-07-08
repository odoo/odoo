# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    zip = fields.Char(related='partner_id.zip', string='Zip', search="_search_zip")

    def _search_zip(self, operator, value):
        return [('partner_id.zip', operator, value)]
