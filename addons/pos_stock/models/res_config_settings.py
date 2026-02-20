# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    update_stock_quantities = fields.Selection(related="company_id.point_of_sale_update_stock_quantities", readonly=False)
    pos_picking_policy = fields.Selection(related='pos_config_id.picking_policy', readonly=False)
    pos_picking_type_id = fields.Many2one(related='pos_config_id.picking_type_id', readonly=False)
    pos_route_id = fields.Many2one(related='pos_config_id.route_id', readonly=False)
    pos_warehouse_id = fields.Many2one(related='pos_config_id.warehouse_id', readonly=False, string="Warehouse (PoS)")
    pos_ship_later = fields.Boolean(related='pos_config_id.ship_later', readonly=False)
