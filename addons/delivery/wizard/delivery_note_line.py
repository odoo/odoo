# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DeliveryNoteWizardLine(models.TransientModel):
    _name = "delivery.note.wizard.line"
    _description = "Delivery Note Line"

    note_id = fields.Many2one(string="Delivery Note Reference", comodel_name="delivery.note.wizard")
    sol_id = fields.Many2one(string="Source Sale Order Line", comodel_name="sale.order.line")
    product_id = fields.Many2one(comodel_name="product.product", related="sol_id.product_id")
    product_image = fields.Image(related="product_id.image_128")
    product_uom_id = fields.Many2one(comodel_name="uom.uom", related="sol_id.product_uom_id")
    product_uom_qty = fields.Float(
        string="Quantity", compute="_compute_product_uom_qty", store=True, readonly=False
    )
    remaining_qty_to_ship = fields.Float(compute="_compute_remaining_qty_to_ship")

    @api.depends("sol_id.product_uom_qty", "sol_id.qty_delivered")
    def _compute_product_uom_qty(self):
        for line in self:
            line.product_uom_qty = line.sol_id.product_uom_qty - line.sol_id.qty_delivered

    @api.depends("sol_id.product_uom_qty", "sol_id.qty_delivered", "product_uom_qty")
    def _compute_remaining_qty_to_ship(self):
        for line in self:
            line.remaining_qty_to_ship = (
                line.sol_id.product_uom_qty - line.product_uom_qty - line.sol_id.qty_delivered
            )

    def _update_sol_qty_delivered(self):
        """Update the quantity delivered of the related sale order line."""
        for line in self:
            line.sol_id.qty_delivered += line.product_uom_qty
