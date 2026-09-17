from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.resource_asset_product.models.resource_asset_part import LEDGER_STATES

_debug = DebugLog(__name__)


class ResourceAssetPart(models.Model):
    _inherit = "resource.asset.part"

    # FIELDS
    stock_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Taken From",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
        help="The stock location the part is consumed from when it is installed. Empty when the installer supplies it.",
    )
    move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Consumption",
        copy=False,
        readonly=True,
        check_company=True,
    )
    removed_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Returned To",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
        help="Where the part taken out is received.",
    )
    removed_move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Return Receipt",
        copy=False,
        readonly=True,
        check_company=True,
    )

    # ACTION METHODS
    def action_receive_removed_part(self):
        for part in self:
            if part.state not in LEDGER_STATES:
                raise UserError(
                    self.env._(
                        "A removed part is received once its replacement is installed."
                    )
                )
            if part.removed_move_id:
                raise UserError(
                    self.env._(
                        "The part removed from %(position)s was already received.",
                        position=part.position_id.name,
                    )
                )
            if not part.removed_location_id:
                raise UserError(
                    self.env._(
                        "Choose where the part removed from %(position)s is received.",
                        position=part.position_id.name,
                    )
                )
            product = part.previous_part_id.product_id or part.product_id
            _debug.lifecycle(
                "removed_part_received",
                part=part,
                product=product,
                location=part.removed_location_id,
                serial=part.removed_serial,
            )
            # sudo: receiving the old part follows from the maintenance, whatever
            # stock rights the technician holds.
            move = part.sudo()._create_part_move(
                product,
                product.property_stock_production,
                part.removed_location_id,
                part.removed_serial,
                create_lot=True,
            )
            part.with_context(asset_part_ledger_write=True).removed_move_id = move
            part.removed_returned = True
        return True

    # LEDGER METHODS
    def _action_install(self):
        from_stock = self.filtered(
            lambda part: part.stock_location_id and not part.move_id
        )
        super()._action_install()
        for part in from_stock:
            _debug.lifecycle(
                "installed_part_consumed",
                part=part,
                location=part.stock_location_id,
                serial=part.serial,
            )
            # sudo: consuming the installed part follows from closing the work.
            move = part.sudo()._create_part_move(
                part.product_id,
                part.stock_location_id,
                part.product_id.property_stock_production,
                part.serial,
            )
            part.with_context(asset_part_ledger_write=True).move_id = move

    # HELPER METHODS
    def _create_part_move(
        self, product, location, location_dest, serial, create_lot=False
    ):
        self.check_singleton()
        if not location_dest or not location:
            raise UserError(
                self.env._(
                    "%(product)s has no production location to consume parts into.",
                    product=product.display_name,
                )
            )
        lot = self.env["stock.lot"]
        if product.tracking != "none":
            if not serial:
                raise UserError(
                    self.env._(
                        "%(product)s is tracked: give the serial of the part at %(position)s.",
                        product=product.display_name,
                        position=self.position_id.name,
                    )
                )
            lot = lot.search(
                [
                    ("product_id", "=", product.id),
                    ("name", "=", serial.strip()),
                    (
                        "company_id",
                        "in",
                        (self.company_id.id or self.env.company.id, False),
                    ),
                ],
                limit=1,
            )
            _debug.logic(
                "part_move_lot_resolved",
                part=self,
                product=product,
                serial=serial,
                lot=lot,
                create_lot=create_lot,
            )
            if not lot and create_lot:
                lot = lot.create(
                    {
                        "name": serial.strip(),
                        "product_id": product.id,
                        "company_id": self.company_id.id or self.env.company.id,
                    }
                )
            if not lot:
                raise UserError(
                    self.env._(
                        "No serial %(serial)s of %(product)s is in stock.",
                        serial=serial,
                        product=product.display_name,
                    )
                )
        company = self.company_id or self.env.company
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "origin": self.maintenance_order_id.name or self.display_name,
                "company_id": company.id,
                "picked": True,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "lot_id": lot.id,
                            "quantity": 1.0,
                            "location_id": location.id,
                            "location_dest_id": location_dest.id,
                            "company_id": company.id,
                        },
                    )
                ],
            }
        )
        move._action_done()
        return move
