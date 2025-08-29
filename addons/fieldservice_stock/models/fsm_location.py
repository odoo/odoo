# Copyright (C) 2018 - TODAY, Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMLocation(models.Model):
    _inherit = "fsm.location"

    inventory_location_id = fields.Many2one(
        "stock.location",
        string="Inventory Location",
        compute="_compute_inventory_location_id",
        store=True,
        readonly=False,
        required=True,
        recursive=True,
        default=lambda self: self.env.ref("stock.stock_location_customers"),
    )
    shipping_address_id = fields.Many2one("res.partner", string="Shipping Location")

    @api.depends("fsm_parent_id", "fsm_parent_id.inventory_location_id")
    def _compute_inventory_location_id(self):
        for rec in self:
            rec.inventory_location_id = rec.fsm_parent_id.inventory_location_id
