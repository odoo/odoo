# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ChoosePickupPoint(models.TransientModel):
    _inherit = 'choose.pickup.point'

    picking_id = fields.Many2one('stock.picking', ondelete="cascade")
