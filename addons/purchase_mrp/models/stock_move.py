from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_cost_ratio(self, quantity):
        self.check_singleton()
        if self.bom_line_id.bom_id.type == "phantom":
            product_uom = self.product_id.uom_id
            uom_quantity = self.product_uom_id._get_quantity_stored(
                self.quantity, product_uom
            )
            if not self.product_uom_id._is_zero_stored(uom_quantity, product_uom):
                unit_kit_purchase = 1
                if self.purchase_line_id:
                    active_moves = self.purchase_line_id.move_ids.filtered(
                        lambda m: (
                            m.state != "cancel"
                            and m.product_id == self.product_id
                            and m.picking_id != self.picking_id
                        ),
                    )
                    active_quantity = quantity + sum(
                        move.product_uom_id._get_quantity_stored(
                            move.quantity, product_uom
                        )
                        for move in active_moves
                    )
                    if active_quantity:
                        unit_kit_purchase = (
                            quantity / active_quantity
                        ) * self.purchase_line_id.product_uom_qty
                return (
                    (self.cost_share / 100)
                    * (quantity / uom_quantity)
                    * unit_kit_purchase
                )
        return super()._get_cost_ratio(quantity)

    def _get_value_from_bill(self, aml):
        value = super()._get_value_from_bill(aml)
        if self.bom_line_id.bom_id.type == "phantom":
            value *= self.cost_share / 100
        return value

    def _get_quantity_from_bill(self, aml, quantity):
        self.check_singleton()
        if self.bom_line_id.bom_id.type == "phantom":
            return aml.product_uom_id._get_quantity_in_unit(
                quantity, self.product_id.uom_id
            )
        return super()._get_quantity_from_bill(aml, quantity)

    def _prepare_phantom_move_vals(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_vals(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals["purchase_line_id"] = self.purchase_line_id.id
        return vals
