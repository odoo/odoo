# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    starshipit_parcel_reference = fields.Char("Starshipit Parcel Reference", copy=False)
    starshipit_return_parcel_reference = fields.Char("Starshipit Return Parcel Reference", copy=False)
