# Copyright Jacques-Etienne Baudoux 2016 Camptocamp
# Copyright Iryna Vyshnevska 2020 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_fillwithstock(self):
        # check source location has no children, i.e. we scanned a bin

        self.ensure_one()
        self._validate_picking()
        context = {
            "active_ids": self._get_movable_quants().ids,
            "active_model": "stock.quant",
            "only_reserved_qty": True,
            "planned": True,
        }
        move_wizard = (
            self.env["wiz.stock.move.location"]
            .with_context(**context)
            .create(
                {
                    "destination_location_id": self.location_dest_id.id,
                    "origin_location_id": self.location_id.id,
                    "picking_type_id": self.picking_type_id.id,
                    "picking_id": self.id,
                }
            )
        )
        move_wizard._onchange_destination_location_id()
        move_wizard.action_move_location()
        return True

    def _validate_picking(self):
        if self.location_id.child_ids:
            raise UserError(_("Please choose a source end location"))
        if self.move_ids:
            raise UserError(_("Moves lines already exists"))

    def _get_movable_quants(self):
        return self.env["stock.quant"].search(
            [
                ("location_id", "=", self.location_id.id),
                ("quantity", ">", 0.0),
            ]
        )
